"""
Serviço de Retrieval-Augmented Generation (RAG).
"""

import logging
import time
from typing import List, Dict, Any, Optional
from utils.telemetry import get_tracer
from opentelemetry import trace
from opentelemetry.trace import SpanKind
from opentelemetry.semconv.trace import SpanAttributes
from core.config import get_settings
from .embedding_service import get_embedding_service
from .llm_service import get_llm_service
from db.repositories.chunk_repository import ChunkRepository
from db.queries.hybrid_search import realizar_busca_hibrida, rerank_results
from processors.normalizers.text_normalizer import clean_query
from utils.metrics_prometheus import (
    record_retrieval_score, record_tokens, 
    record_documents_retrieved, record_llm_error
)
import tiktoken  # Para contagem de tokens

logger = logging.getLogger(__name__)


class RAGService:
    """
    Serviço de Retrieval-Augmented Generation.

    Orquestra o processo completo de RAG:
    1. Preparação e limpeza da consulta
    2. Geração de embeddings
    3. Recuperação de documentos relevantes
    4. Montagem do contexto para o LLM
    5. Geração da resposta pelo LLM
    """

    def __init__(self):
        """
        Inicializa o serviço RAG.
        """
        self.settings = get_settings()
        self.embedding_service = get_embedding_service()
        self.llm_service = get_llm_service()
        self.tracer = get_tracer(__name__)

    def apply_quality_boost(self, chunks):
        """
        Aplica um boost de relevância baseado na qualidade dos chunks.
        
        Args:
            chunks: Lista de chunks recuperados
            
        Returns:
            Lista de chunks com scores ajustados pela qualidade
        """
        
        for chunk in chunks:
            # Verificar se o chunk tem metadados de qualidade
            if chunk.metadados and 'chunk_quality' in chunk.metadados:
                quality_score = float(chunk.metadados['chunk_quality'])
                
                # Aplicar boost baseado na qualidade (até 10%)
                quality_boost = quality_score * 0.1
                
                # Ajustar o score combinado
                chunk.combined_score = chunk.combined_score * (1 + quality_boost)
                
                logger.debug(
                    f"Aplicado boost de qualidade: {quality_boost:.3f} ao chunk {chunk.id}. "
                    f"Score original: {chunk.combined_score/(1+quality_boost):.3f}, "
                    f"Score ajustado: {chunk.combined_score:.3f}"
                )
                
            # Considerar também a estratégia de chunking
            if chunk.metadados and 'chunking_strategy' in chunk.metadados:
                strategy = chunk.metadados['chunking_strategy']
                
                # Ajustar scores com base na estratégia
                # Podemos favorecer certas estratégias com base em testes
                strategy_boost = 0
                if strategy == "header_based":
                    # Favorecer chunks baseados em cabeçalhos para consultas que parecem buscar tópicos específicos
                    strategy_boost = 0.05
                elif strategy == "hybrid":
                    # Híbrido é bom para consultas gerais
                    strategy_boost = 0.02
                
                # Aplicar o boost
                if strategy_boost > 0:
                    chunk.combined_score = chunk.combined_score * (1 + strategy_boost)
                    
                    logger.debug(
                        f"Aplicado boost de estratégia {strategy}: {strategy_boost:.3f} ao chunk {chunk.id}. "
                        f"Score ajustado: {chunk.combined_score:.3f}"
                    )
        
        # Reordenar após aplicar os boosts
        return sorted(chunks, key=lambda x: x.combined_score, reverse=True)

    
    async def process_query(
        self,
        query: str,
        filtro_documentos: Optional[List[int]] = None,
        max_results: Optional[int] = None,
        vector_weight: Optional[float] = None,
        include_debug_info: bool = False,
    ) -> Dict[str, Any]:
        """
        Processa uma consulta usando o pipeline RAG completo.

        Args:
            query: Consulta do usuário
            filtro_documentos: IDs de documentos para filtrar (opcional)
            max_results: Número máximo de resultados (opcional)
            vector_weight: Peso da busca vetorial vs. textual (opcional)
            include_debug_info: Se True, inclui informações de depuração na resposta

        Returns:
            dict: Resposta gerada e informações de depuração (se solicitado)
        """
        with self.tracer.start_as_current_span(
            "rag_service.process_query",
            kind=SpanKind.SERVER
        ) as span:
            start_time_total = time.time()

            span.set_attribute("query.text", query)
            span.set_attribute("query.length", len(query))
            if filtro_documentos:
                span.set_attribute("query.filter_docs_count", len(filtro_documentos))
            span.set_attribute("param.max_results", max_results if max_results is not None else self.settings.MAX_RESULTS)
            span.set_attribute("param.vector_weight", vector_weight if vector_weight is not None else self.settings.VECTOR_SEARCH_WEIGHT)
            span.set_attribute("param.include_debug_info", include_debug_info)

            try:
                # 1. Preparar e limpar a consulta
                with self.tracer.start_as_current_span("query_processing.clean") as clean_span:
                    clean_query_text = clean_query(query)
                    clean_span.set_attribute("query.clean_text", clean_query_text)
                    clean_span.set_attribute("query.clean_length", len(clean_query_text))

                if not clean_query_text:
                    span.set_attribute("result.empty_query", True)
                    return {"response": "Não entendi sua consulta. Pode reformulá-la?"}

                # 2. Gerar embedding da consulta
                with self.tracer.start_as_current_span("query_embedding.generate") as embed_span:
                    query_embedding = self.embedding_service.embed_text(clean_query_text)
                    if query_embedding:
                        embed_span.set_attribute("embedding.vector_length", len(query_embedding))
                    else:
                        embed_span.set_attribute("embedding.generation_failed", True)

                # 3. Recuperar documentos relevantes
                with self.tracer.start_as_current_span("document_retrieval.hybrid_search") as search_span:
                    alpha = vector_weight if vector_weight is not None else self.settings.VECTOR_SEARCH_WEIGHT
                    limit = max_results if max_results is not None else self.settings.MAX_RESULTS
                    initial_retrieval_limit = limit * 2
                    query_specificity = len(clean_query_text.split()) / 5
                    adjusted_threshold = min(0.7, max(0.5, 0.5 + (query_specificity * 0.05)))

                    search_span.set_attribute("retrieval.type", "hybrid")
                    search_span.set_attribute("retrieval.alpha", alpha)
                    search_span.set_attribute("retrieval.initial_limit", initial_retrieval_limit)
                    search_span.set_attribute("retrieval.final_limit", limit)
                    search_span.set_attribute("retrieval.threshold", adjusted_threshold)
                    if filtro_documentos:
                        search_span.set_attribute("retrieval.filter_docs_count", len(filtro_documentos))

                    logger.info(f"Realizando busca híbrida com alpha={alpha:.2f}, limite inicial={initial_retrieval_limit}, threshold={adjusted_threshold:.2f}")

                    retrieved_chunks = realizar_busca_hibrida(
                        query_text=clean_query_text,
                        query_embedding=query_embedding,
                        limite=initial_retrieval_limit,
                        alpha=alpha,
                        filtro_documentos=filtro_documentos,
                        threshold=adjusted_threshold,
                    )
                    search_span.set_attribute("retrieval.initial_chunks_count", len(retrieved_chunks))
                    record_documents_retrieved(len(retrieved_chunks))

                # 4. Reranking para melhorar a relevância
                with self.tracer.start_as_current_span("document_processing.rerank") as rerank_span:
                    rerank_span.set_attribute("reranking.initial_chunks_count", len(retrieved_chunks))
                    ranked_chunks = rerank_results(retrieved_chunks, clean_query_text)
                    rerank_span.set_attribute("reranking.ranked_chunks_count", len(ranked_chunks))

                # 5. Aplicar boost de qualidade
                with self.tracer.start_as_current_span("document_processing.quality_boost") as boost_span:
                    boost_span.set_attribute("quality_boost.initial_chunks_count", len(ranked_chunks))
                    quality_boosted_chunks = self.apply_quality_boost(ranked_chunks)
                    boost_span.set_attribute("quality_boost.boosted_chunks_count", len(quality_boosted_chunks))

                # 6. Limitar ao número final de resultados
                final_limit = max_results if max_results is not None else self.settings.MAX_RESULTS
                final_chunks = quality_boosted_chunks[:final_limit]
                span.set_attribute("retrieval.final_chunks_count", len(final_chunks))

                # Registrar métricas Prometheus
                for chunk in final_chunks:
                    record_retrieval_score(chunk.combined_score, "combined")
                    if hasattr(chunk, 'similarity_score'):
                         record_retrieval_score(chunk.similarity_score, "vector")
                    if hasattr(chunk, 'text_score'):
                        record_retrieval_score(chunk.text_score, "text")

                # Estimar tokens do contexto
                context_tokens = sum(len(chunk.texto.split()) for chunk in final_chunks)
                record_tokens(context_tokens, "context")
                span.set_attribute("context.tokens", context_tokens)

                # 7. Preparar contexto para o LLM
                with self.tracer.start_as_current_span("context_preparation") as ctx_prep_span:
                    context = ""
                    context_tokens = 0
                    tokenizer = tiktoken.encoding_for_model("gpt-4")

                    if not final_chunks:
                        logger.warning(f"Nenhum documento relevante encontrado para a consulta: '{query}'")
                        context = "Não foram encontrados documentos relevantes para esta consulta específica."
                        ctx_prep_span.set_attribute("context.empty", True)
                    else:
                        ctx_prep_span.set_attribute("context.empty", False)
                        ctx_prep_span.set_attribute("context.chunks_count", len(final_chunks))
                        chunk_texts = []
                        for i, chunk in enumerate(final_chunks):
                            strategy_info = ""
                            if chunk.metadados and 'chunking_strategy' in chunk.metadados:
                                strategy = chunk.metadados['chunking_strategy']
                                strategy_info = f" [estratégia: {strategy}]"
                                ctx_prep_span.set_attribute(f"context.chunk_{i}.strategy", strategy)

                            chunk_header = f"Contexto {i+1} [relevância: {chunk.combined_score:.2f}]{strategy_info}\n"
                            chunk_content = chunk.texto
                            chunk_texts.append(chunk_header + chunk_content)

                            # Contagem de tokens
                            try:
                                chunk_tokens = len(tokenizer.encode(chunk_content))
                                context_tokens += chunk_tokens
                                ctx_prep_span.set_attribute(f"context.chunk_{i}.tokens", chunk_tokens)
                            except Exception as tokenizer_error:
                                logger.warning(f"Erro ao tokenizar chunk {i}: {tokenizer_error}")
                                ctx_prep_span.set_attribute(f"context.chunk_{i}.tokenization_error", True)

                        context = "\n\n".join(chunk_texts)

                    ctx_prep_span.set_attribute("context.length", len(context))
                    ctx_prep_span.set_attribute("context.tokens", context_tokens)
                    record_tokens(context_tokens, "context")

                # 8. Construir o prompt para o LLM
                with self.tracer.start_as_current_span("prompt_building") as prompt_span:
                    system_prompt = f"""Você é um assistente especializado em valoração de tecnologias relacionadas ao Patrimônio Genético Nacional e Conhecimentos Tradicionais Associados.

                    Responda ao usuário usando as informações fornecidas nos documentos do contexto. Cada contexto tem uma pontuação de relevância associada a ele - contextos com pontuação mais alta são mais relevantes para o tópico atual.

                    IMPORTANTE: 
                    - Não mencione os "contextos" ou "documentos" na sua resposta. O usuário não sabe que você está consultando diferentes fontes.
                    - Identifique e responda apropriadamente a saudações e interações sociais básicas sem tentar forçar informações técnicas.
                    - Para consultas técnicas, apresente a informação de forma natural e fluida.

                    Se realmente não houver informações suficientes nos contextos para responder adequadamente, você pode indicar isso de forma sutil, sugerindo que há limitações nas informações disponíveis, mas tente sempre fornecer valor com o que você tem.

                    As respostas devem ser em português brasileiro formal, mantendo a terminologia técnica apropriada ao tema de biodiversidade, conhecimentos tradicionais e propriedade intelectual quando relevante.
                    """

                    user_prompt_content = f"Documentos:\n{context}\n\nPergunta: {query}"

                    # Contar tokens do prompt
                    try:
                         system_tokens = len(tokenizer.encode(system_prompt))
                         user_tokens = len(tokenizer.encode(user_prompt_content))
                         prompt_tokens = system_tokens + user_tokens
                         prompt_span.set_attribute("prompt.system_tokens", system_tokens)
                         prompt_span.set_attribute("prompt.user_tokens", user_tokens)
                         prompt_span.set_attribute("prompt.total_tokens", prompt_tokens)
                         record_tokens(prompt_tokens, "prompt")
                    except Exception as tokenizer_error:
                        logger.warning(f"Erro ao tokenizar prompt: {tokenizer_error}")
                        prompt_span.set_attribute("prompt.tokenization_error", True)

                    prompt_span.set_attribute("prompt.system_length", len(system_prompt))
                    prompt_span.set_attribute("prompt.user_length", len(user_prompt_content))

                # 9. Gerar resposta com o LLM
                with self.tracer.start_as_current_span("llm_generation.generate") as llm_span:
                    response_text = await self.llm_service.generate_text(
                        system_prompt=system_prompt, user_prompt=user_prompt_content
                    )
                    llm_span.set_attribute("llm.response_length", len(response_text))

                    # Contar tokens da resposta e registrar métrica
                    try:
                        response_tokens = len(tokenizer.encode(response_text))
                        llm_span.set_attribute("llm.response_tokens", response_tokens)
                        record_tokens(response_tokens, "response")
                    except Exception as tokenizer_error:
                        logger.warning(f"Erro ao tokenizar resposta LLM: {tokenizer_error}")
                        llm_span.set_attribute("llm.response_tokenization_error", True)

                # 10. Preparar resultado
                processing_time_total = time.time() - start_time_total
                span.set_attribute("processing.total_time_ms", int(processing_time_total * 1000))

                result = {"response": response_text, "processing_time": processing_time_total}

                # Adicionar informações de depuração se solicitado
                if include_debug_info:
                    # Incluir informações sobre estratégias de chunking
                    chunk_strategies = []
                    for chunk in final_chunks:
                        if chunk.metadados and 'chunking_strategy' in chunk.metadados:
                            chunk_strategies.append(chunk.metadados['chunking_strategy'])
                        else:
                            chunk_strategies.append("unknown")
                    
                    debug_info = {
                        "query": query,
                        "clean_query": clean_query_text,
                        "num_results": len(final_chunks),
                        "sources": [chunk.arquivo_origem for chunk in final_chunks],
                        "scores": [round(chunk.combined_score, 3) for chunk in final_chunks],
                        "chunking_strategies": chunk_strategies,
                        "threshold": adjusted_threshold,
                        "contexts": [chunk.texto for chunk in final_chunks]
                    }
                    result["debug_info"] = debug_info

                span.set_status(trace.StatusCode.OK)
                return result

            except Exception as e:
                logger.error(f"Erro durante processamento RAG para query '{query}': {e}", exc_info=True)
                span.set_status(trace.Status(trace.StatusCode.ERROR, description=str(e)))
                span.record_exception(e)
                span.set_attribute("error.type", type(e).__name__)

                record_llm_error("rag_service")

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


# Instância singleton para uso em toda a aplicação
_rag_service_instance: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """
    Retorna a instância do serviço RAG.

    Returns:
        RAGService: Instância do serviço
    """
    global _rag_service_instance

    if _rag_service_instance is None:
        _rag_service_instance = RAGService()

    return _rag_service_instance
