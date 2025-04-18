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
from infrastructure.telemetry.opentelemetry import get_tracer
from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode # Importar Status e StatusCode
from infrastructure.metrics.prometheus.metrics_prometheus import (
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

    # Método interno para contagem de tokens
    def _count_tokens(self, text: str) -> int:
        """ Conta tokens usando o tokenizador ou fallback. """
        if not text: return 0
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except Exception:
                # Fallback simples se encode falhar
                return len(text.split())
        else:
            # Fallback se o tokenizador não foi inicializado
            return len(text.split())

    # Método interno para re-ranking (chama a interface do reranker)
    async def _rerank_results(self, chunks: List[Chunk], query: str) -> List[Tuple[Chunk, float]]:
         """ Reordena os chunks usando o ReRanker injetado e retorna tuplas (Chunk, score). """
         logger.info(f"Iniciando re-ranking de {len(chunks)} chunks via UseCase...")
         if not chunks: return []
         # Chama o método da interface ReRanker
         reranked_list_with_scores = await self._reranker.rerank(query=query, chunks=chunks)
         return reranked_list_with_scores

    # --- Métodos Privados Refatorados ---

    async def _prepare_query(self, query: str) -> Tuple[str, Embedding]:
        """
        Limpa a query e gera seu embedding.

        Returns:
            Tuple[str, Embedding]: A query limpa e o objeto Embedding.
        Raises:
            ValueError: Se a query limpa for vazia ou a geração do embedding falhar.
        """
        with self.tracer.start_as_current_span("query_processing.prepare_and_embed") as prep_span:
            prep_span.set_attribute("query.original_text", query)
            clean_query_text = clean_query(query)
            prep_span.set_attribute("query.clean_text", clean_query_text)
            prep_span.set_attribute("query.clean_length", len(clean_query_text))

            if not clean_query_text:
                logger.warning("Query resultou em texto vazio após limpeza.")
                prep_span.set_attribute("result.empty_query", True)
                prep_span.set_status(Status(StatusCode.ERROR, description="Clean query is empty"))
                raise ValueError("Não entendi sua consulta. Pode reformulá-la?")

            start_embed = time.time()
            try:
                query_embedding_object: Embedding = await self._embedding_provider.embed_text(clean_query_text)
                embed_duration_ms = int((time.time() - start_embed) * 1000)
                prep_span.set_attribute("embedding.duration_ms", embed_duration_ms)

                if query_embedding_object and query_embedding_object.vector:
                    prep_span.set_attribute("embedding.vector_length", len(query_embedding_object.vector))
                    prep_span.set_status(Status(StatusCode.OK))
                    return clean_query_text, query_embedding_object
                else:
                    logger.error("Falha ao gerar embedding para a consulta (vetor vazio ou None retornado).")
                    prep_span.set_attribute("embedding.generation_failed", True)
                    prep_span.set_status(Status(StatusCode.ERROR, description="Embedding generation failed"))
                    raise ValueError("Falha ao gerar embedding válido para a consulta.")

            except Exception as e:
                logger.error(f"Erro inesperado durante geração do embedding: {e}", exc_info=True)
                prep_span.set_attribute("embedding.generation_failed", True)
                prep_span.record_exception(e)
                prep_span.set_status(Status(StatusCode.ERROR, description=f"Embedding exception: {e}"))
                raise ValueError(f"Erro ao gerar embedding para a consulta: {e}") from e

    async def _retrieve_chunks(
        self,
        clean_query: str,
        query_embedding_vector: List[float],
        initial_limit: int,
        filter_document_ids: Optional[List[int]] = None,
    ) -> Tuple[List[Tuple[Chunk, float]], List[Tuple[Chunk, float]]]:
        """
        Executa a busca híbrida (vetorial e por keyword) no repositório de chunks.
        """
        # Busca Vetorial
        with self.tracer.start_as_current_span("vector_search.find_similar") as vec_span:
            vec_span.set_attribute("param.initial_limit", initial_limit)
            vec_span.set_attribute("param.has_filter", filter_document_ids is not None)
            start_vec_search = time.time()
            vector_results: List[Tuple[Chunk, float]] = await self._chunk_repository.find_similar_chunks(
                embedding_vector=query_embedding_vector,
                limit=initial_limit,
                filter_document_ids=filter_document_ids,
            )
            vec_duration_ms = int((time.time() - start_vec_search) * 1000)
            vec_span.set_attribute("duration_ms", vec_duration_ms)
            vec_span.set_attribute("result.chunks_found_count", len(vector_results))
            logger.info(f"Busca vetorial retornou {len(vector_results)} chunks em {vec_duration_ms} ms.")
            vec_span.set_status(Status(StatusCode.OK))

        # Busca por Keyword
        with self.tracer.start_as_current_span("keyword_search.find_by_keyword") as key_span:
            key_span.set_attribute("param.initial_limit", initial_limit)
            key_span.set_attribute("param.has_filter", filter_document_ids is not None)
            start_kw_search = time.time()
            keyword_results: List[Tuple[Chunk, float]] = await self._chunk_repository.find_by_keyword(
                query=clean_query,
                limit=initial_limit,
                filter_document_ids=filter_document_ids,
            )
            kw_duration_ms = int((time.time() - start_kw_search) * 1000)
            key_span.set_attribute("duration_ms", kw_duration_ms)
            key_span.set_attribute("result.chunks_found_count", len(keyword_results))
            logger.info(f"Busca por keyword retornou {len(keyword_results)} chunks em {kw_duration_ms} ms.")
            key_span.set_status(Status(StatusCode.OK))

        return vector_results, keyword_results

    async def _rank_and_filter_chunks(
        self,
        vector_results: List[Tuple[Chunk, float]],
        keyword_results: List[Tuple[Chunk, float]],
        clean_query: str,
        final_limit: int,
        rrf_k: int = 60,
    ) -> Tuple[List[Tuple[Chunk, float]], Dict[int, float]]:
        """
        Combina resultados com RRF, re-rankeia e aplica o limite final.
        """
        # Reciprocal Rank Fusion (RRF)
        with self.tracer.start_as_current_span("ranking.rrf") as rrf_span:
            start_rrf = time.time()
            rrf_ranked_chunks, hybrid_scores = reciprocal_rank_fusion(
                [vector_results, keyword_results], k=rrf_k
            )
            rrf_duration_ms = int((time.time() - start_rrf) * 1000)
            rrf_span.set_attribute("duration_ms", rrf_duration_ms)
            rrf_span.set_attribute("rrf.input_vector_count", len(vector_results))
            rrf_span.set_attribute("rrf.input_keyword_count", len(keyword_results))
            rrf_span.set_attribute("rrf.output_chunks_count", len(rrf_ranked_chunks))
            rrf_span.set_attribute("rrf.k_param", rrf_k)
            logger.info(f"RRF (k={rrf_k}) combinou {len(vector_results)}+{len(keyword_results)} resultados em {len(rrf_ranked_chunks)} chunks únicos em {rrf_duration_ms} ms.")
            rrf_span.set_status(Status(StatusCode.OK))

        # Re-ranking
        reranked_chunks_with_scores: List[Tuple[Chunk, float]] = []
        if rrf_ranked_chunks:
            with self.tracer.start_as_current_span("ranking.rerank_after_rrf") as rerank_span:
                rerank_span.set_attribute("reranking.input_chunks_count", len(rrf_ranked_chunks))
                start_rerank = time.time()
                reranked_chunks_with_scores = await self._rerank_results(rrf_ranked_chunks, clean_query)
                rerank_duration_ms = int((time.time() - start_rerank) * 1000)
                rerank_span.set_attribute("duration_ms", rerank_duration_ms)
                rerank_span.set_attribute("reranking.output_chunks_count", len(reranked_chunks_with_scores))
                logger.info(f"Re-ranking após RRF retornou {len(reranked_chunks_with_scores)} chunks com scores em {rerank_duration_ms} ms.")
                rerank_span.set_status(Status(StatusCode.OK))
        else:
            logger.info("Pulando re-ranking pois RRF não retornou chunks.")

        # Limitar ao número FINAL de resultados
        final_chunks_with_scores = reranked_chunks_with_scores[:final_limit]

        # Calcular scores RRF apenas para os chunks finais
        final_rrf_scores: Dict[int, float] = {
            chunk.id: hybrid_scores.get(chunk.id, 0.0)
            for chunk, _ in final_chunks_with_scores if chunk.id is not None and chunk.id in hybrid_scores
        }

        logger.info(f"Ranking e filtragem finalizados. {len(final_chunks_with_scores)} chunks selecionados.")
        return final_chunks_with_scores, final_rrf_scores

    def _build_llm_context_and_prompt(
        self,
        final_chunks_with_scores: List[Tuple[Chunk, float]],
        query: str,
    ) -> Tuple[str, str, int, int]:
        """
        Constrói a string de contexto e monta o prompt para o LLM.
        """
        # Preparar contexto
        with self.tracer.start_as_current_span("context_preparation") as ctx_prep_span:
            context = ""
            context_tokens = 0
            if not final_chunks_with_scores:
                logger.warning(f"Nenhum chunk relevante encontrado para a consulta: '{query}'")
                context = "Não foram encontrados documentos relevantes para esta consulta específica."
                ctx_prep_span.set_attribute("context.empty", True)
            else:
                ctx_prep_span.set_attribute("context.empty", False)
                ctx_prep_span.set_attribute("context.chunks_count", len(final_chunks_with_scores))
                chunk_texts = []
                for i, (chunk, reranker_score) in enumerate(final_chunks_with_scores):
                    rerank_pos = i + 1
                    score_info = f"[Rank: {rerank_pos}, Score: {reranker_score:.4f}]"
                    chunk_header = f"Contexto {i+1} {score_info}\n"
                    chunk_content = chunk.text
                    full_chunk_text = chunk_header + chunk_content
                    chunk_texts.append(full_chunk_text)
                    context_tokens += self._count_tokens(chunk_content)
                context = "\n\n".join(chunk_texts)

            ctx_prep_span.set_attribute("context.length", len(context))
            ctx_prep_span.set_attribute("context.tokens", context_tokens)
            record_tokens(context_tokens, "context")
            ctx_prep_span.set_status(Status(StatusCode.OK))

        # Construir prompt
        with self.tracer.start_as_current_span("prompt_building") as prompt_span:
            system_prompt = self.settings.RAG_SYSTEM_PROMPT or """Você é um assistente prestativo. Use o contexto fornecido para responder."""
            user_prompt_llm = f"Contexto:\n{context}\n\nPergunta: {query}"
            prompt_tokens = self._count_tokens(system_prompt) + self._count_tokens(user_prompt_llm)
            prompt_span.set_attribute("prompt.system_length", len(system_prompt))
            prompt_span.set_attribute("prompt.user_length", len(user_prompt_llm))
            prompt_span.set_attribute("prompt.total_tokens", prompt_tokens)
            record_tokens(prompt_tokens, "prompt")
            prompt_span.set_status(Status(StatusCode.OK))

        return context, user_prompt_llm, context_tokens, prompt_tokens

    async def _generate_final_response(self, query: str, context: str) -> Tuple[str, int]:
        """
        Gera a resposta final usando o LLM Provider.
        """
        with self.tracer.start_as_current_span("llm_generation.generate") as llm_span:
            start_llm = time.time()
            try:
                response_text = await self._llm_provider.generate_response(
                    prompt=query, context=context,
                )
                llm_duration_ms = int((time.time() - start_llm) * 1000)
                llm_span.set_attribute("duration_ms", llm_duration_ms)
                llm_span.set_attribute("llm.response_length", len(response_text))

                response_tokens = self._count_tokens(response_text)
                llm_span.set_attribute("llm.response_tokens", response_tokens)
                record_tokens(response_tokens, "response")
                llm_span.set_status(Status(StatusCode.OK))

                return response_text, response_tokens

            except Exception as e:
                 logger.error(f"Erro durante chamada ao LLM Provider: {e}", exc_info=True)
                 llm_span.record_exception(e)
                 llm_span.set_status(Status(StatusCode.ERROR, description=f"LLM Provider error: {e}"))
                 record_llm_error("llm_provider_error")
                 raise # Re-lança para ser capturada pelo `execute`

    def _assemble_result(
        self,
        response_text: str,
        processing_time: float,
        query: str,
        clean_query_text: str,
        final_chunks_with_scores: List[Tuple[Chunk, float]],
        final_rrf_scores: Dict[int, float],
        context: str,
        context_tokens: int,
        prompt_tokens: int,
        response_tokens: int,
        initial_search_limit: int,
    ) -> Dict[str, Any]:
        """
        Monta o dicionário final de resultado, incluindo informações de debug.
        """
        final_chunks: List[Chunk] = [chunk for chunk, score in final_chunks_with_scores]
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

        final_reranker_scores_debug: Dict[int, float] = {
            c.id: float(score) for c, score in final_chunks_with_scores if c.id is not None
        }

        debug_info = {
            "query": query,
            "clean_query": clean_query_text,
            "num_results": len(final_chunks),
            "retrieved_chunk_ids_after_rerank": [c.id for c in final_chunks],
            "retrieved_reranker_scores": final_reranker_scores_debug,
            "retrieved_rrf_scores": final_rrf_scores,
            "context_used_length": len(context),
            "context_used_tokens": context_tokens,
            "prompt_tokens": prompt_tokens,
            "response_tokens": response_tokens,
            "initial_search_limit": initial_search_limit,
            "final_chunk_details": final_chunk_details_list
        }

        result = {
            "response": response_text,
            "processing_time": processing_time,
            "debug_info": debug_info
        }

        logger.debug(f"Resultado final montado para query '{query[:50]}...'. Response length: {len(response_text)}")
        return result

    # --- Método Principal de Execução (Orquestrador) ---
    @log_execution
    @log_execution_time
    @track_use_case_metrics
    async def execute(
        self,
        query: str,
        filtro_documentos: Optional[List[int]] = None,
        max_results: Optional[int] = None,
        include_debug_info: bool = False, # Usado implicitamente por _assemble_result
    ) -> Dict[str, Any]:
        """
        Executa o pipeline RAG completo para a consulta dada (Refatorado).
        Orquestra a preparação, recuperação, ranqueamento, geração e montagem do resultado.
        """
        logger.info(f"Executando ProcessQueryUseCase para query: '{query[:50]}...'")
        with self.tracer.start_as_current_span(
            "process_query_use_case.execute", kind=SpanKind.SERVER
        ) as span:
            start_time_total = time.time()
            limit = max_results if max_results is not None else self.settings.MAX_RESULTS
            # Definir atributos gerais do span
            span.set_attribute("query.text", query)
            span.set_attribute("query.length", len(query))
            if filtro_documentos:
                span.set_attribute("query.filter_docs_count", len(filtro_documentos))
            span.set_attribute("param.max_results", limit)

            try:
                # --- Orquestração ---
                # 1. Preparar Query e Embedding
                clean_query_text, query_embedding_object = await self._prepare_query(query)
                query_embedding_vector = query_embedding_object.vector

                # 2. Recuperar Chunks (Busca Híbrida)
                initial_search_limit = limit * 4
                span.set_attribute("param.initial_search_limit", initial_search_limit)
                vector_results, keyword_results = await self._retrieve_chunks(
                    clean_query=clean_query_text,
                    query_embedding_vector=query_embedding_vector,
                    initial_limit=initial_search_limit,
                    filter_document_ids=filtro_documentos
                )

                # 3. Combinar, Re-rankear e Filtrar Chunks
                final_chunks_with_scores, final_rrf_scores = await self._rank_and_filter_chunks(
                    vector_results=vector_results,
                    keyword_results=keyword_results,
                    clean_query=clean_query_text,
                    final_limit=limit
                )

                # 4. Construir Contexto e Prompt para LLM
                context, _, context_tokens, prompt_tokens = self._build_llm_context_and_prompt(
                    final_chunks_with_scores=final_chunks_with_scores,
                    query=query
                )

                # 5. Gerar resposta com o LLM
                response_text, response_tokens = await self._generate_final_response(query, context)

                # 6. Montar Resultado Final
                processing_time_total = time.time() - start_time_total
                result = self._assemble_result(
                    response_text=response_text,
                    processing_time=processing_time_total,
                    query=query,
                    clean_query_text=clean_query_text,
                    final_chunks_with_scores=final_chunks_with_scores,
                    final_rrf_scores=final_rrf_scores,
                    context=context,
                    context_tokens=context_tokens,
                    prompt_tokens=prompt_tokens,
                    response_tokens=response_tokens,
                    initial_search_limit=initial_search_limit,
                )
                # --- Fim da Orquestração ---

                # Registrar métricas agregadas e status OK
                span.set_attribute("processing.total_time_ms", int(processing_time_total * 1000))
                for chunk_id, rrf_score in final_rrf_scores.items():
                     record_retrieval_score(rrf_score, "hybrid_rrf") # Métricas Prometheus
                span.set_status(Status(StatusCode.OK))
                logger.info(f"ProcessQueryUseCase concluído com sucesso para query '{query[:50]}...' em {processing_time_total:.2f}s")
                return result

            except ValueError as ve:
                 # Erros de validação/preparação
                 logger.warning(f"Erro de validação durante ProcessQueryUseCase para query '{query}': {ve}")
                 if span.is_recording():
                    span.set_status(Status(StatusCode.INVALID_ARGUMENT, description=str(ve)))
                    span.set_attribute("error.type", type(ve).__name__)
                 return {"response": str(ve)} # Retorna mensagem de erro amigável

            except Exception as e:
                 # Erros inesperados (LLM, Repositório, etc.)
                 processing_time_total = time.time() - start_time_total # Calcula tempo mesmo em erro
                 logger.error(f"Erro inesperado ({type(e).__name__}) durante ProcessQueryUseCase para query '{query}' após {processing_time_total:.2f}s: {e}", exc_info=True)
                 if span.is_recording():
                    span.set_status(Status(StatusCode.ERROR, description=str(e)))
                    span.record_exception(e)
                    span.set_attribute("error.type", type(e).__name__)
                 record_llm_error("process_query_use_case_error") # Métrica de erro do use case
                 # Retornar resposta genérica de erro
                 return {
                     "response": "Desculpe, ocorreu um erro interno ao processar sua consulta. A equipe foi notificada."
                 }

