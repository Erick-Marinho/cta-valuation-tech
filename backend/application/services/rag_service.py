"""
Serviço de Retrieval-Augmented Generation (RAG).
"""

import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from utils.telemetry import get_tracer
from opentelemetry import trace
from opentelemetry.trace import SpanKind
from opentelemetry.semconv.trace import SpanAttributes
from config.config import get_settings
# from db.repositories.chunk_repository import ChunkRepository
# from db.queries.hybrid_search import realizar_busca_hibrida, rerank_results
from infrastructure.processors.normalizers.text_normalizer import clean_query
from utils.metrics_prometheus import (
    record_retrieval_score,
    record_tokens,
    record_documents_retrieved,
    record_llm_error,
)
import tiktoken  # Para contagem de tokens

# Import temporário direto da infraestrutura (VIOLA Clean Architecture)
# TODO: Refatorar RAGService para usar a interface EmbeddingProvider injetada
from infrastructure.external_services.embedding.huggingface_embedding_provider import HuggingFaceEmbeddingProvider
# O RAGService precisará instanciar ou receber uma instância disso temporariamente.
# Como o HuggingFaceEmbeddingProvider não tem mais get_embedding_service(),
# a forma como RAGService o obtém/usa precisará ser ajustada também.
# Talvez ele precise chamar get_embedding_provider() de dependencies.py?

# Importar Interfaces e Repositório
from application.interfaces.embedding_provider import EmbeddingProvider
from application.interfaces.llm_provider import LLMProvider
from domain.repositories.chunk_repository import ChunkRepository
from domain.aggregates.document.chunk import Chunk # Importar entidade Chunk
from application.interfaces.reranker import ReRanker # Importar interface ReRanker
from domain.value_objects.embedding import Embedding # <-- Adicionar ou verificar import

logger = logging.getLogger(__name__)


class RAGService:
    """
    Serviço de Aplicação para Retrieval-Augmented Generation.

    Orquestra o processo completo de RAG:
    1. Preparação e limpeza da consulta
    2. Geração de embeddings
    3. Recuperação de chunks relevantes (usando ChunkRepository)
    4. Re-ranking e processamento dos chunks (Placeholder)
    5. Montagem do contexto para o LLM
    6. Geração da resposta pelo LLM (usando LLMProvider)
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        llm_provider: LLMProvider,
        chunk_repository: ChunkRepository,
        reranker: ReRanker, # <-- Adicionar reranker
    ):
        """
        Inicializa o serviço RAG com suas dependências.
        """
        self.settings = get_settings()
        self._embedding_provider = embedding_provider # Usar prefixo '_' para indicar injeção
        self._llm_provider = llm_provider
        self._chunk_repository = chunk_repository
        self._reranker = reranker # <-- Armazenar reranker
        self.tracer = get_tracer(__name__)
        # Inicializar tokenizador aqui para reuso
        try:
            self.tokenizer = tiktoken.encoding_for_model("gpt-4") # ou cl100k_base
        except Exception:
            logger.warning("Tiktoken não encontrado, contagem de tokens será baseada em split()")
            self.tokenizer = None

    def _count_tokens(self, text: str) -> int:
        """ Conta tokens usando o tokenizador ou fallback. """
        if not text: return 0
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except Exception:
                return len(text.split()) # Fallback
        else:
            return len(text.split()) # Fallback

    async def _rerank_results(self, chunks: List[Chunk], query: str) -> List[Tuple[Chunk, float]]:
         """ Reordena os chunks e retorna tuplas (Chunk, score). """
         logger.info(f"Iniciando re-ranking de {len(chunks)} chunks...")
         if not chunks: return []
         # Chama o método da interface ReRanker (que agora retorna tuplas)
         reranked_list_with_scores = await self._reranker.rerank(query=query, chunks=chunks)
         return reranked_list_with_scores

    async def process_query(
        self,
        query: str,
        filtro_documentos: Optional[List[int]] = None,
        max_results: Optional[int] = None,
        include_debug_info: bool = False,
    ) -> Dict[str, Any]:
        """
        Processa uma consulta usando o pipeline RAG completo.
        """
        with self.tracer.start_as_current_span(
            "rag_service.process_query", kind=SpanKind.SERVER
        ) as span:
            start_time_total = time.time()

            # Atributos iniciais do Span
            span.set_attribute("query.text", query)
            span.set_attribute("query.length", len(query))
            if filtro_documentos:
                span.set_attribute("query.filter_docs_count", len(filtro_documentos))
            limit = max_results if max_results is not None else self.settings.MAX_RESULTS
            span.set_attribute("param.max_results", limit)
            span.set_attribute("param.include_debug_info", include_debug_info)

            try:
                # 1. Preparar e limpar a consulta
                with self.tracer.start_as_current_span("query_processing.clean") as clean_span:
                    clean_query_text = clean_query(query) # Função utilitária
                    clean_span.set_attribute("query.clean_text", clean_query_text)
                    clean_span.set_attribute("query.clean_length", len(clean_query_text))

                if not clean_query_text:
                    span.set_attribute("result.empty_query", True)
                    return {"response": "Não entendi sua consulta. Pode reformulá-la?"}

                # 2. Gerar embedding da consulta
                with self.tracer.start_as_current_span("query_embedding.generate") as embed_span:
                    start_embed = time.time()
                    # Chamada retorna um objeto Embedding
                    query_embedding_object: Embedding = await self._embedding_provider.embed_text(clean_query_text) # <-- MUDANÇA: Renomear variável

                    embed_span.set_attribute("duration_ms", int((time.time() - start_embed) * 1000))

                    # Acessar o vetor para validação e uso posterior
                    query_embedding_vector = query_embedding_object.vector # <-- MUDANÇA: Extrair .vector

                    if query_embedding_vector: # Verificar se o vetor não está vazio/nulo
                        embed_span.set_attribute("embedding.vector_length", len(query_embedding_vector)) # <-- Usar o vetor
                    else:
                        embed_span.set_attribute("embedding.generation_failed", True)
                        # Considerar se a falha deve resultar em vetor zero ou levantar erro
                        logger.error("Falha ao gerar embedding para a consulta (vetor vazio retornado).")
                        # Você pode optar por retornar um erro aqui ou continuar com um vetor zero
                        # Se continuar, certifique-se de que query_embedding_vector seja tratado adequadamente abaixo
                        query_embedding_vector = [] # Ou [0.0] * dimensão_esperada se preferir

                    if not query_embedding_vector: # Checar novamente após possível fallback
                         raise ValueError("Falha ao gerar embedding válido para a consulta.")

                # 3. Busca Vetorial no Repositório de Chunks
                with self.tracer.start_as_current_span("vector_search.find_similar") as search_span:
                    start_search = time.time()
                    search_span.set_attribute("vector.query_vector_length", len(query_embedding_vector)) # <-- Usar o vetor
                    search_span.set_attribute("param.limit", limit)
                    if filtro_documentos:
                         search_span.set_attribute("param.filter_doc_ids", str(filtro_documentos))

                    # O método find_similar_chunks provavelmente espera List[float]
                    similar_chunks = await self._chunk_repository.find_similar_chunks(
                        embedding_vector=query_embedding_vector, # <-- MUDANÇA: Passar o vetor numérico
                        limit=limit,
                        filter_document_ids=filtro_documentos,
                    )
                    search_span.set_attribute("duration_ms", int((time.time() - start_search) * 1000))
                    search_span.set_attribute("result.chunks_found_count", len(similar_chunks))

                # 4. Re-ranking (Obtém Lista de Tuplas)
                with self.tracer.start_as_current_span("document_processing.rerank") as rerank_span:
                    rerank_span.set_attribute("reranking.input_chunks_count", len(similar_chunks))
                    # _rerank_results agora retorna List[Tuple[Chunk, float]]
                    reranked_chunks_with_scores: List[Tuple[Chunk, float]] = await self._rerank_results(similar_chunks, clean_query_text) # <-- MUDANÇA: Capturar tuplas
                    rerank_span.set_attribute("reranking.output_chunks_count", len(reranked_chunks_with_scores))
                # -----------------------------------------

                # --- 6. Limitar ao número FINAL de resultados ---
                # Aplicar limite na lista de tuplas
                final_chunks_with_scores = reranked_chunks_with_scores[:limit] # <-- MUDANÇA: Limitar tuplas
                # Extrair apenas os chunks finais para o contexto, se necessário
                final_chunks: List[Chunk] = [chunk for chunk, score in final_chunks_with_scores] # <-- Extrair chunks
                # Criar um dicionário de scores para fácil acesso pelo ID do chunk
                final_scores: Dict[int, float] = {chunk.id: score for chunk, score in final_chunks_with_scores if chunk.id is not None} # <-- Criar dict de scores

                logger.info(f"Limitando contexto final para {len(final_chunks)} chunks após rerank.")
                span.set_attribute("retrieval.final_chunks_count", len(final_chunks))
                # --------------------------------------------

                # Usar os scores do reranker para métricas
                for chunk, score in final_chunks_with_scores:
                     # Usar o score do reranker (item[1] da tupla)
                     record_retrieval_score(score, "cross_encoder_rerank") # <-- MUDANÇA: Usar score do reranker e nomear métrica

                # 7. Preparar contexto para o LLM (usar score do reranker)
                with self.tracer.start_as_current_span("context_preparation") as ctx_prep_span:
                    context = ""
                    context_tokens = 0
                    if not final_chunks:
                        logger.warning(f"Nenhum chunk relevante encontrado para a consulta: '{query}'")
                        context = "Não foram encontrados documentos relevantes para esta consulta específica."
                        ctx_prep_span.set_attribute("context.empty", True)
                    else:
                        ctx_prep_span.set_attribute("context.empty", False)
                        ctx_prep_span.set_attribute("context.chunks_count", len(final_chunks))
                        chunk_texts = []
                        # Iterar sobre as tuplas para ter acesso ao score
                        for i, (chunk, score) in enumerate(final_chunks_with_scores): # <-- MUDANÇA: Iterar sobre tuplas
                            rerank_pos = i + 1
                            # Usar o score do reranker formatado
                            score_info = f"[Rank: {rerank_pos}, Score: {score:.4f}]" # <-- MUDANÇA: Usar score real
                            chunk_header = f"Contexto {i+1} {score_info}\n"
                            chunk_content = chunk.text
                            chunk_texts.append(chunk_header + chunk_content)
                            context_tokens += self._count_tokens(chunk_content)

                        context = "\n\n".join(chunk_texts)

                    ctx_prep_span.set_attribute("context.length", len(context))
                    ctx_prep_span.set_attribute("context.tokens", context_tokens)
                    record_tokens(context_tokens, "context") # Métrica

                # 8. Construir o prompt para o LLM (mantido)
                with self.tracer.start_as_current_span("prompt_building") as prompt_span:
                    # Prompt do sistema pode ser configurável via settings
                    system_prompt = self.settings.RAG_SYSTEM_PROMPT or """Você é um assistente prestativo. Use o contexto fornecido para responder."""
                    user_prompt_llm = f"Contexto:\n{context}\n\nPergunta: {query}"

                    prompt_tokens = self._count_tokens(system_prompt) + self._count_tokens(user_prompt_llm)
                    prompt_span.set_attribute("prompt.total_tokens", prompt_tokens)
                    record_tokens(prompt_tokens, "prompt") # Métrica

                # 9. Gerar resposta com o LLM (Usando LLMProvider injetado)
                with self.tracer.start_as_current_span("llm_generation.generate") as llm_span:
                    start_llm = time.time()
                    # Chamar o método da interface LLMProvider
                    response_text = await self._llm_provider.generate_response(
                        prompt=query, # Passar a pergunta original ou a limpa? Original.
                        context=context,
                        # history=... # Adicionar se tiver histórico
                        # max_tokens=... # Pode ser configurável
                        # temperature=... # Pode ser configurável
                    )
                    llm_span.set_attribute("duration_ms", int((time.time() - start_llm) * 1000))
                    llm_span.set_attribute("llm.response_length", len(response_text))

                    response_tokens = self._count_tokens(response_text)
                    llm_span.set_attribute("llm.response_tokens", response_tokens)
                    record_tokens(response_tokens, "response") # Métrica

                # 10. Preparar resultado (adicionar score ao debug info)
                processing_time_total = time.time() - start_time_total
                span.set_attribute("processing.total_time_ms", int(processing_time_total * 1000))

                result = {
                    "response": response_text,
                    "processing_time": processing_time_total,
                }

                if include_debug_info:
                    final_chunk_details_list = []
                    # Iterar sobre as tuplas para ter acesso ao score
                    for rank, (c, score) in enumerate(final_chunks_with_scores):
                        chunk_detail = {
                            "id": c.id,
                            "doc_id": c.document_id,
                            "page": c.page_number,
                            "pos": c.position,
                            "text_content": c.text,
                            "final_rank": rank + 1,
                            # Converter score para float padrão
                            "reranker_score": float(score) # <-- CORREÇÃO: Converter para float()
                        }
                        final_chunk_details_list.append(chunk_detail)

                    # Criar dicionário de scores convertendo para float padrão
                    final_scores_float: Dict[int, float] = { # <-- CORREÇÃO: Novo dict com float
                        chunk.id: float(score)
                        for chunk, score in final_chunks_with_scores if chunk.id is not None
                    }

                    debug_info = {
                        "query": query,
                        "clean_query": clean_query_text,
                        "num_results": len(final_chunks),
                        "retrieved_chunk_ids_after_rerank": [c.id for c in final_chunks],
                        # Usar o dicionário com scores convertidos
                        "retrieved_reranker_scores": final_scores_float, # <-- CORREÇÃO: Usar dict com float
                        "context_used_length": len(context),
                        "context_used_tokens": context_tokens,
                        "final_chunk_details": final_chunk_details_list
                    }
                    result["debug_info"] = debug_info

                span.set_status(trace.StatusCode.OK)
                return result

            except Exception as e:
                logger.error(f"Erro durante processamento RAG para query '{query}': {e}", exc_info=True)
                # Garantir que o span capture a exceção e marque como erro
                if trace.get_current_span().is_recording():
                    span.set_status(trace.Status(trace.StatusCode.ERROR, description=str(e)))
                    span.record_exception(e)
                    span.set_attribute("error.type", type(e).__name__)

                record_llm_error("rag_service") # Métrica de erro genérico RAG

                return {
                    "response": "Desculpe, ocorreu um erro ao processar sua consulta. Por favor, tente novamente."
                }

    def get_similar_questions(self, query: str, limit: int = 5) -> List[str]:
        """
        Retorna perguntas similares à consulta do usuário.
        Útil para sugestões de perguntas relacionadas.

        Args:
            query: Consulta do usuário
            limit: Número máximo de perguntas a retornar

        Returns:
            list: Lista de perguntas similares
        """
        # Implementação simplificada - em uma versão real,
        # poderíamos ter um banco de perguntas frequentes com embeddings
        # e fazer busca por similaridade

        # Por enquanto, retornamos uma lista estática
        return [
            "O que é CTA Value Tech?",
            "Como funciona a valoração de tecnologias com acesso ao PGN?",
            "Quais são os princípios da Convenção sobre a Diversidade Biológica?",
            "Como são calculados os royalties da sociobiodiversidade?",
            "O que são Conhecimentos Tradicionais Associados?",
        ][:limit]
