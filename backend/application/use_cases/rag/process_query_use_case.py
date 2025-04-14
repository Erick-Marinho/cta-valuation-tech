import logging
import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple # Importar tipos necessários

# Importar Interfaces e Repositórios do Domínio/Aplicação
from application.interfaces.embedding_provider import EmbeddingProvider
from application.interfaces.llm_provider import LLMProvider
from domain.repositories.chunk_repository import ChunkRepository
from application.interfaces.reranker import ReRanker

# Importar Value Objects ou Entidades do Domínio, se necessário diretamente
from domain.aggregates.document.chunk import Chunk
from domain.value_objects.embedding import Embedding

# Importar helpers/utils (RRF, normalização, etc.)
from application.ranking.rrf import reciprocal_rank_fusion
from infrastructure.processors.normalizers.text_normalizer import clean_query # Ajustar import se necessário
from config.config import get_settings # Para settings

# Importar ferramentas de observabilidade
# from utils.telemetry import get_tracer # <-- Linha antiga comentada/removida
from infrastructure.telemetry.opentelemetry import get_tracer # <-- Nova linha
from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode # Importar Status e StatusCode
# from utils.metrics_prometheus import ( # Importar métricas # <-- Linha antiga comentada/removida
from infrastructure.metrics.prometheus.metrics_prometheus import ( # <-- Linha corrigida
    record_retrieval_score,
    record_tokens,
    record_llm_error,
)
import tiktoken # Se a contagem de tokens for feita aqui

# --- Adicionar import dos decorators ---
from application.decorators.logging_decorator import log_execution
from application.decorators.timing_decorator import log_execution_time
from application.decorators.metrics_decorator import track_use_case_metrics # Novo import
# ---------------------------------------

logger = logging.getLogger(__name__)


class ProcessQueryUseCase:
    """
    Caso de Uso para processar uma consulta do usuário via pipeline RAG.

    Orquestra a busca híbrida, RRF, re-ranking e geração de resposta pelo LLM.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        llm_provider: LLMProvider,
        chunk_repository: ChunkRepository,
        reranker: ReRanker,
    ):
        """ Inicializa o caso de uso com suas dependências. """
        self.settings = get_settings()
        self._embedding_provider = embedding_provider
        self._llm_provider = llm_provider
        self._chunk_repository = chunk_repository
        self._reranker = reranker
        self.tracer = get_tracer(__name__)
        # Inicializar tokenizador se a contagem for feita aqui
        try:
            self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        except Exception:
            logger.warning("Tiktoken não encontrado no ProcessQueryUseCase.")
            self.tokenizer = None
        # Verificar se dependências foram injetadas corretamente
        if not all([embedding_provider, llm_provider, chunk_repository, reranker]):
            logger.critical("ProcessQueryUseCase inicializado com dependências ausentes!")
            raise ValueError("Todas as dependências devem ser fornecidas para ProcessQueryUseCase.")

    # Método interno para contagem de tokens (copiado de RAGService)
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

    # Método interno para re-ranking (copiado de RAGService)
    # Recebe List[Chunk], chama self._reranker, retorna List[Tuple[Chunk, float]]
    async def _rerank_results(self, chunks: List[Chunk], query: str) -> List[Tuple[Chunk, float]]:
         """ Reordena os chunks usando o ReRanker injetado e retorna tuplas (Chunk, score). """
         logger.info(f"Iniciando re-ranking de {len(chunks)} chunks via UseCase...")
         if not chunks: return []
         # Chama o método da interface ReRanker (que agora retorna tuplas)
         reranked_list_with_scores = await self._reranker.rerank(query=query, chunks=chunks)
         return reranked_list_with_scores

    # --- Aplicar todos os decorators ---
    @log_execution
    @log_execution_time
    @track_use_case_metrics # Aplicar o novo decorator
    # -----------------------------------
    async def execute(
        self,
        query: str,
        filtro_documentos: Optional[List[int]] = None,
        max_results: Optional[int] = None,
        include_debug_info: bool = False,
    ) -> Dict[str, Any]:
        """
        Executa o pipeline RAG completo para a consulta dada.

        Args:
            query: A consulta do usuário.
            filtro_documentos: Lista opcional de IDs de documentos para filtrar a busca.
            max_results: Número máximo de chunks a serem usados no contexto final.
            include_debug_info: Se True, inclui informações detalhadas de depuração no resultado.

        Returns:
            Um dicionário contendo a resposta e opcionalmente informações de debug.
        """
        logger.info(f"Executando ProcessQueryUseCase para query: '{query[:50]}...'")
        with self.tracer.start_as_current_span(
            "process_query_use_case.execute", kind=SpanKind.SERVER # Nome do Span atualizado
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
                    query_embedding_object: Embedding = await self._embedding_provider.embed_text(clean_query_text)
                    embed_span.set_attribute("duration_ms", int((time.time() - start_embed) * 1000))
                    query_embedding_vector = query_embedding_object.vector

                    if query_embedding_vector:
                        embed_span.set_attribute("embedding.vector_length", len(query_embedding_vector))
                    else:
                        embed_span.set_attribute("embedding.generation_failed", True)
                        logger.error("Falha ao gerar embedding para a consulta (vetor vazio retornado).")
                        query_embedding_vector = []

                    if not query_embedding_vector:
                         raise ValueError("Falha ao gerar embedding válido para a consulta.")

                # --- Busca Híbrida ---
                # 3a. Busca Vetorial
                with self.tracer.start_as_current_span("vector_search.find_similar") as vec_span:
                     initial_search_limit = limit * 4
                     vec_span.set_attribute("param.initial_limit", initial_search_limit)
                     vector_results: List[Tuple[Chunk, float]] = await self._chunk_repository.find_similar_chunks(
                         embedding_vector=query_embedding_vector,
                         limit=initial_search_limit,
                         filter_document_ids=filtro_documentos,
                     )
                     vec_span.set_attribute("result.chunks_found_count", len(vector_results))
                     logger.info(f"Busca vetorial retornou {len(vector_results)} chunks.")

                # 3b. Busca por Keyword
                with self.tracer.start_as_current_span("keyword_search.find_by_keyword") as key_span:
                     key_span.set_attribute("param.initial_limit", initial_search_limit)
                     keyword_results: List[Tuple[Chunk, float]] = await self._chunk_repository.find_by_keyword(
                         query=clean_query_text,
                         limit=initial_search_limit,
                         filter_document_ids=filtro_documentos,
                     )
                     key_span.set_attribute("result.chunks_found_count", len(keyword_results))
                     logger.info(f"Busca por keyword retornou {len(keyword_results)} chunks.")
                # --------------------

                # 4. Reciprocal Rank Fusion (RRF)
                with self.tracer.start_as_current_span("ranking.rrf") as rrf_span:
                     rrf_ranked_chunks, hybrid_scores = reciprocal_rank_fusion(
                         [vector_results, keyword_results], k=60
                     )
                     rrf_span.set_attribute("rrf.output_chunks_count", len(rrf_ranked_chunks))
                     logger.info(f"RRF combinou resultados em {len(rrf_ranked_chunks)} chunks únicos.")
                # --------------------

                # 5. Re-ranking (Opcional, mas geralmente útil após RRF)
                reranked_chunks_with_scores: List[Tuple[Chunk, float]] = []
                if rrf_ranked_chunks:
                     with self.tracer.start_as_current_span("ranking.rerank_after_rrf") as rerank_span:
                          rerank_span.set_attribute("reranking.input_chunks_count", len(rrf_ranked_chunks))
                          reranked_chunks_with_scores = await self._rerank_results(rrf_ranked_chunks, clean_query_text)
                          rerank_span.set_attribute("reranking.output_chunks_count", len(reranked_chunks_with_scores))
                          logger.info(f"Re-ranking após RRF retornou {len(reranked_chunks_with_scores)} chunks com scores.")
                else:
                     logger.info("Pulando re-ranking pois RRF não retornou chunks.")
                     reranked_chunks_with_scores = []
                # --------------------

                # 6. Limitar ao número FINAL de resultados
                final_chunks_with_scores = reranked_chunks_with_scores[:limit]
                final_chunks: List[Chunk] = [chunk for chunk, score in final_chunks_with_scores]
                final_reranker_scores: Dict[int, float] = {
                    chunk.id: float(score) for chunk, score in final_chunks_with_scores if chunk.id is not None
                }
                final_rrf_scores: Dict[int, float] = {
                     chunk.id: hybrid_scores.get(chunk.id, 0.0) for chunk in final_chunks if chunk.id is not None
                }

                logger.info(f"Contexto final limitado a {len(final_chunks)} chunks.")
                span.set_attribute("retrieval.final_chunks_count", len(final_chunks))
                # --------------------

                # Usar scores RRF para métricas
                for chunk_id, rrf_score in final_rrf_scores.items():
                     record_retrieval_score(rrf_score, "hybrid_rrf")

                # 7. Preparar contexto para o LLM
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
                        for i, (chunk, reranker_score) in enumerate(final_chunks_with_scores):
                            rerank_pos = i + 1
                            score_info = f"[Rank: {rerank_pos}, Score: {reranker_score:.4f}]"
                            chunk_header = f"Contexto {i+1} {score_info}\n"
                            chunk_content = chunk.text
                            chunk_texts.append(chunk_header + chunk_content)
                            context_tokens += self._count_tokens(chunk_content)
                        context = "\n\n".join(chunk_texts)

                    ctx_prep_span.set_attribute("context.length", len(context))
                    ctx_prep_span.set_attribute("context.tokens", context_tokens)
                    record_tokens(context_tokens, "context")

                # 8. Construir o prompt para o LLM
                with self.tracer.start_as_current_span("prompt_building") as prompt_span:
                    system_prompt = self.settings.RAG_SYSTEM_PROMPT or """Você é um assistente prestativo. Use o contexto fornecido para responder."""
                    user_prompt_llm = f"Contexto:\n{context}\n\nPergunta: {query}"
                    prompt_tokens = self._count_tokens(system_prompt) + self._count_tokens(user_prompt_llm)
                    prompt_span.set_attribute("prompt.total_tokens", prompt_tokens)
                    record_tokens(prompt_tokens, "prompt")

                # 9. Gerar resposta com o LLM
                with self.tracer.start_as_current_span("llm_generation.generate") as llm_span:
                    start_llm = time.time()
                    response_text = await self._llm_provider.generate_response(
                        prompt=query, context=context,
                    )
                    llm_span.set_attribute("duration_ms", int((time.time() - start_llm) * 1000))
                    llm_span.set_attribute("llm.response_length", len(response_text))
                    response_tokens = self._count_tokens(response_text)
                    llm_span.set_attribute("llm.response_tokens", response_tokens)
                    record_tokens(response_tokens, "response")

                # 10. Preparar resultado
                processing_time_total = time.time() - start_time_total
                span.set_attribute("processing.total_time_ms", int(processing_time_total * 1000))

                result = {
                    "response": response_text,
                    "processing_time": processing_time_total,
                }

                # --- Bloco de criação do debug_info (agora incondicional) ---
                final_chunk_details_list = []
                for rank, (c, reranker_score) in enumerate(final_chunks_with_scores):
                     chunk_detail = {
                        "id": c.id,
                        "doc_id": c.document_id,
                        "page": c.page_number,
                        "pos": c.position,
                        "text_content": c.text,
                        "final_rank": rank + 1,
                        "reranker_score": float(reranker_score),
                        "rrf_score": final_rrf_scores.get(c.id)
                     }
                     final_chunk_details_list.append(chunk_detail)

                debug_info = {
                    "query": query,
                    "clean_query": clean_query_text,
                    "num_results": len(final_chunks),
                    "retrieved_chunk_ids_after_rerank": [c.id for c in final_chunks],
                    "retrieved_reranker_scores": final_reranker_scores,
                    "retrieved_rrf_scores": final_rrf_scores,
                    "context_used_length": len(context),
                    "context_used_tokens": context_tokens,
                    "final_chunk_details": final_chunk_details_list,
                    "initial_search_limit": initial_search_limit
                }
                result["debug_info"] = debug_info # Adiciona a chave ao dict result
                # --- Fim do Bloco ---

                span.set_status(Status(StatusCode.OK))
                return result

            except Exception as e:
                 logger.error(f"Erro durante ProcessQueryUseCase para query '{query}': {e}", exc_info=True)
                 if span.is_recording(): # Verificar se span está ativo
                    span.set_status(Status(StatusCode.ERROR, description=str(e))) # Usar Status importado
                    span.record_exception(e)
                    span.set_attribute("error.type", type(e).__name__)

                 record_llm_error("process_query_use_case") # Métrica de erro

                 return {
                     "response": "Desculpe, ocorreu um erro ao processar sua consulta. Por favor, tente novamente."
                 }
