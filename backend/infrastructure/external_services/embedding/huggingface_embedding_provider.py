"""
Serviço para geração e manipulação de embeddings.
"""

import time
import logging
from typing import List, Dict, Any, Optional
from langchain_huggingface import HuggingFaceEmbeddings
from config.config import get_settings
from infrastructure.processors.normalizers.text_normalizer import clean_text_for_embedding
from opentelemetry import trace
from infrastructure.telemetry.opentelemetry import get_tracer
from infrastructure.metrics.prometheus.metrics_prometheus import (
    record_embedding_time,
    update_embedding_cache_metrics,
)
from opentelemetry.trace import SpanKind, Status, StatusCode
from application.interfaces.embedding_provider import EmbeddingProvider
import asyncio
from sentence_transformers import SentenceTransformer
from domain.value_objects.embedding import Embedding

logger = logging.getLogger(__name__)

settings = get_settings()


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    """
    Serviço para geração de embeddings para textos.

    Responsável por:
    - Inicializar e gerenciar modelos de embedding
    - Gerar embeddings para textos e consultas
    - Implementar cache para embeddings frequentes
    - Fornecer métricas e logging
    """

    _model: SentenceTransformer = None
    _model_name: str = ""
    _device: str = ""

    def __init__(self):
        """
        Inicializa o serviço de embeddings.
        """
        with get_tracer(__name__).start_as_current_span(
            "embedding_service.__init__"
        ) as init_span:
            self.settings = get_settings()
            self._cache: Dict[int, List[float]] = {}
            self._cache_hits: int = 0
            self._cache_misses: int = 0
            self._total_embeddings: int = 0
            self.tracer = get_tracer(__name__)

            init_span.set_attribute("cache.type", "in_memory")
            init_span.set_attribute("cache.max_size", 10000)

            self._initialize_model()

    def _initialize_model(self):
        """
        Inicializa o modelo de embeddings.
        """
        with self.tracer.start_as_current_span(
            "embedding_service.initialize_model", kind=SpanKind.INTERNAL
        ) as span:
            try:
                if HuggingFaceEmbeddingProvider._model is None:
                    HuggingFaceEmbeddingProvider._model_name = self.settings.EMBEDDING_MODEL
                    HuggingFaceEmbeddingProvider._device = 'cuda' if self.settings.USE_GPU else 'cpu'

                    span.set_attribute("embedding.model_name", HuggingFaceEmbeddingProvider._model_name)
                    span.set_attribute("embedding.device", HuggingFaceEmbeddingProvider._device)
                    logger.info(f"Carregando modelo SentenceTransformer: {HuggingFaceEmbeddingProvider._model_name} no dispositivo: {HuggingFaceEmbeddingProvider._device}")
                    try:
                        start_load = time.time()
                        HuggingFaceEmbeddingProvider._model = SentenceTransformer(
                            HuggingFaceEmbeddingProvider._model_name, device=HuggingFaceEmbeddingProvider._device
                        )
                        load_time = time.time() - start_load
                        logger.info(f"Modelo SentenceTransformer '{HuggingFaceEmbeddingProvider._model_name}' carregado em {load_time:.2f}s.")
                        span.set_attribute("embedding.load_time_ms", int(load_time * 1000))
                        span.set_status(Status(StatusCode.OK))
                    except Exception as e:
                        logger.error(f"Falha ao carregar modelo SentenceTransformer '{HuggingFaceEmbeddingProvider._model_name}': {e}", exc_info=True)
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, description=str(e)))
                        raise RuntimeError(f"Falha ao inicializar HuggingFaceEmbeddingProvider: {e}") from e
                else:
                    logger.info(f"Reutilizando modelo SentenceTransformer já carregado: {HuggingFaceEmbeddingProvider._model_name}")
                    span.set_attribute("embedding.model_name", HuggingFaceEmbeddingProvider._model_name)
                    span.set_attribute("embedding.device", HuggingFaceEmbeddingProvider._device)
                    span.set_status(Status(StatusCode.OK, "Modelo reutilizado."))

                self.model = HuggingFaceEmbeddingProvider._model
                self.model_name = HuggingFaceEmbeddingProvider._model_name
                self.device = HuggingFaceEmbeddingProvider._device

                test_text = "verificação de dimensão"
                with self.tracer.start_as_current_span(
                    "embedding_service.initialize_model.dimension_check"
                ) as check_span:
                    test_embedding = self.model.encode([test_text], convert_to_numpy=True, show_progress_bar=False)
                    embedding_dim = len(test_embedding[0])
                    check_span.set_attribute("embedding.dimension", embedding_dim)

                span.set_attribute("model.dimension", embedding_dim)
                configured_dim = self.settings.EMBEDDING_DIMENSION
                span.set_attribute("model.configured_dimension", configured_dim)

                if embedding_dim != configured_dim:
                    warning_msg = f"Dimensão do embedding ({embedding_dim}) difere da configurada ({configured_dim})"
                    logger.warning(warning_msg)
                    span.set_attribute("model.dimension_mismatch", True)

                logger.info(
                    f"Modelo de embeddings '{HuggingFaceEmbeddingProvider._model_name}' inicializado. Dimensão: {embedding_dim}. Tempo: {load_time:.2f}s"
                )
                span.set_status(Status(StatusCode.OK))

            except Exception as e:
                logger.error(
                    f"Falha crítica ao inicializar modelo de embeddings '{HuggingFaceEmbeddingProvider._model_name}': {e}",
                    exc_info=True,
                )
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, description=str(e)))
                span.set_attribute("error.type", type(e).__name__)
                raise RuntimeError(
                    f"Falha ao inicializar modelo de embeddings: {e}"
                ) from e

    async def embed_text(self, text: str) -> Embedding:
        """
        Gera embedding para um texto único.

        Args:
            text: Texto para gerar embedding

        Returns:
            Embedding: Objeto de embedding
        """
        with self.tracer.start_as_current_span(
            "embedding_service.embed_text", kind=SpanKind.INTERNAL
        ) as span:
            start_time = time.time()

            span.set_attribute("vector.text_length", len(text))
            span.set_attribute("model.name", self.settings.EMBEDDING_MODEL)

            if not text or not text.strip():
                logger.warning("Tentativa de embedding para texto vazio.")
                span.set_attribute("vector.text_empty", True)
                span.set_status(
                    Status(StatusCode.OK, "Texto vazio, retornando vetor zero.")
                )
                return Embedding(vector=[0.0] * self.settings.EMBEDDING_DIMENSION)

            clean_text = clean_text_for_embedding(text).lower()
            span.set_attribute("vector.cleaned_text_length", len(clean_text))

            cache_key = hash(clean_text)
            cached_embedding = self._cache.get(cache_key)

            if cached_embedding is not None:
                self._cache_hits += 1
                span.set_attribute("cache.hit", True)
                update_embedding_cache_metrics("hits", self._cache_hits)
                hit_ratio = self._cache_hits / max(
                    1, self._cache_hits + self._cache_misses
                )
                update_embedding_cache_metrics("hit_ratio", hit_ratio)
                span.set_attribute("cache.hit_ratio", hit_ratio)

                elapsed_time = time.time() - start_time
                record_embedding_time(elapsed_time, operation_type="single")
                span.set_attribute("duration_ms", int(elapsed_time * 1000))
                span.set_attribute("vector.dimension", len(cached_embedding))
                span.set_status(Status(StatusCode.OK))
                return Embedding(vector=cached_embedding)

            span.set_attribute("cache.hit", False)
            self._cache_misses += 1
            update_embedding_cache_metrics("misses", self._cache_misses)
            hit_ratio = self._cache_hits / max(1, self._cache_hits + self._cache_misses)
            update_embedding_cache_metrics("hit_ratio", hit_ratio)
            span.set_attribute("cache.hit_ratio", hit_ratio)

            try:
                embeddings_list: List[Embedding] = await self.embed_batch([text])
                if embeddings_list and len(embeddings_list) == 1:
                    embedding_obj = embeddings_list[0]
                    span.set_attribute("embedding.vector_length", len(embedding_obj.vector))
                    span.set_status(Status(StatusCode.OK))

                    if cache_key not in self._cache and len(self._cache) < 10000:
                        self._cache[cache_key] = embedding_obj.vector
                        update_embedding_cache_metrics("size", len(self._cache))

                    return embedding_obj
                else:
                    logger.error(f"embed_batch não retornou o resultado esperado para texto único: {text[:100]}...")
                    span.set_status(Status(StatusCode.ERROR, "Resultado inesperado de embed_batch"))
                    zero_vec = [0.0] * self.settings.EMBEDDING_DIMENSION
                    return Embedding(vector=zero_vec)

            except Exception as e:
                elapsed_time = time.time() - start_time
                record_embedding_time(elapsed_time, operation_type="single")
                logger.exception(f"Erro ao gerar embedding para texto único: {e}")
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, description=str(e)))
                span.set_attribute("error.type", type(e).__name__)
                zero_vec = [0.0] * self.settings.EMBEDDING_DIMENSION
                return Embedding(vector=zero_vec)

    async def embed_batch(self, texts: List[str]) -> List[Embedding]:
        """
        Gera embeddings para múltiplos textos em lote.

        Args:
            texts: Lista de textos para gerar embeddings

        Returns:
            list: Lista de objetos de embedding
        """
        with self.tracer.start_as_current_span(
            "embedding_service.embed_batch", kind=SpanKind.INTERNAL
        ) as span:
            start_time = time.time()
            batch_size = len(texts)
            span.set_attribute("vector.batch_size", batch_size)
            span.set_attribute("model.name", self.settings.EMBEDDING_MODEL)

            if not texts:
                span.set_status(Status(StatusCode.OK, "Batch vazio."))
                return []

            clean_texts_map: Dict[str, List[int]] = {}
            original_clean_texts: List[Optional[str]] = [None] * batch_size
            for i, text in enumerate(texts):
                if not text or not text.strip():
                    original_clean_texts[i] = None
                    continue
                clean_t = clean_text_for_embedding(text).lower()
                original_clean_texts[i] = clean_t
                if clean_t not in clean_texts_map:
                    clean_texts_map[clean_t] = []
                clean_texts_map[clean_t].append(i)

            avg_len = sum(len(t) for t in clean_texts_map.keys()) / max(
                1, len(clean_texts_map)
            )
            span.set_attribute("vector.unique_texts_count", len(clean_texts_map))
            span.set_attribute("vector.avg_unique_text_length", avg_len)

            embeddings: List[Optional[Embedding]] = [None] * batch_size
            texts_to_embed_list: List[str] = []
            cache_hits_in_batch = 0
            initial_miss_count = self._cache_misses

            for clean_text, indices in clean_texts_map.items():
                cache_key = hash(clean_text)
                cached_embedding = self._cache.get(cache_key)
                if cached_embedding is not None:
                    cache_hits_in_batch += len(indices)
                    self._cache_hits += len(indices)
                    for i in indices:
                        embeddings[i] = Embedding(vector=cached_embedding)
                else:
                    texts_to_embed_list.append(clean_text)

            if cache_hits_in_batch > 0:
                update_embedding_cache_metrics("hits", self._cache_hits)

            uncached_count = len(texts_to_embed_list)
            span.set_attribute("cache.batch_hits_count", cache_hits_in_batch)
            span.set_attribute("cache.batch_unique_misses_count", uncached_count)

            if uncached_count > 0:
                self._cache_misses += uncached_count
                span.set_attribute("cache.misses_increment", uncached_count)
                update_embedding_cache_metrics("misses", self._cache_misses)

                try:
                    def sync_embed_documents():
                        return self.model.encode(texts_to_embed_list, convert_to_numpy=True, show_progress_bar=False)

                    new_embeddings_np = await asyncio.to_thread(sync_embed_documents)
                    new_embeddings_vectors: List[List[float]] = [embedding.tolist() for embedding in new_embeddings_np]

                    self._total_embeddings += uncached_count

                    cache_updated = False
                    if len(self._cache) < 10000:
                        space_available = 10000 - len(self._cache)
                        can_add_count = min(space_available, len(new_embeddings_vectors))
                        for i in range(can_add_count):
                            clean_text = texts_to_embed_list[i]
                            embedding = new_embeddings_vectors[i]
                            cache_key = hash(clean_text)
                            self._cache[cache_key] = embedding
                            cache_updated = True
                        span.set_attribute("cache.added_count", can_add_count)
                        if can_add_count < len(new_embeddings_vectors):
                            span.set_attribute("cache.full", True)

                    embedding_idx = 0
                    for clean_text, original_indices in clean_texts_map.items():
                        if any(embeddings[idx] is None for idx in original_indices):
                            if embedding_idx < len(new_embeddings_vectors):
                                vector = new_embeddings_vectors[embedding_idx]
                                embedding_obj = Embedding(vector=vector)
                                for original_index in original_indices:
                                    if embeddings[original_index] is None:
                                        embeddings[original_index] = embedding_obj
                                embedding_idx += 1
                            else:
                                logger.error("Índice de embedding fora dos limites, inconsistência.")
                                # Lidar com erro (ex: preencher com zero vector ou levantar exceção)

                    if cache_updated:
                        update_embedding_cache_metrics("size", len(self._cache))

                except Exception as e:
                    logger.error(
                        f"Erro ao gerar embeddings em lote para {uncached_count} textos: {e}",
                        exc_info=True,
                    )
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, description=str(e)))
                    span.set_attribute("error.type", type(e).__name__)
                    zero_vec = [0.0] * self.settings.EMBEDDING_DIMENSION
                    zero_embedding = Embedding(vector=zero_vec)
                    for i in range(len(embeddings)):
                        if embeddings[i] is None:
                            embeddings[i] = zero_embedding

            final_embeddings: List[Embedding] = []
            zero_vec = [0.0] * self.settings.EMBEDDING_DIMENSION
            zero_embedding = Embedding(vector=zero_vec)
            for emb in embeddings:
                final_embeddings.append(emb if emb is not None else zero_embedding)

            hit_ratio = self._cache_hits / max(1, self._cache_hits + self._cache_misses)
            update_embedding_cache_metrics("hit_ratio", hit_ratio)

            elapsed_time = time.time() - start_time
            record_embedding_time(elapsed_time, operation_type="batch")

            if span.is_recording():
                span.set_attribute("cache.hit_ratio", hit_ratio)
                span.set_attribute("duration_ms", int(elapsed_time * 1000))
                if final_embeddings:
                    span.set_attribute("vector.dimension", len(final_embeddings[0].vector))

                current_status = getattr(span, "status", None)
                if (
                    current_status is None
                    or current_status.status_code != StatusCode.ERROR
                ):
                    span.set_status(Status(StatusCode.OK))

            return final_embeddings

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do cache de embeddings.

        Returns:
            dict: Estatísticas do cache
        """
        with self.tracer.start_as_current_span(
            "embedding_service.get_cache_stats"
        ) as span:
            total_requests = self._cache_hits + self._cache_misses
            hit_rate = (
                self._cache_hits / max(1, total_requests) if total_requests > 0 else 0.0
            )

            update_embedding_cache_metrics("size", len(self._cache))
            update_embedding_cache_metrics("hits", self._cache_hits)
            update_embedding_cache_metrics("misses", self._cache_misses)
            update_embedding_cache_metrics("hit_ratio", hit_rate)

            stats = {
                "cache_size": len(self._cache),
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "hit_rate": hit_rate,
                "total_embeddings_generated": self._total_embeddings,
            }
            for key, value in stats.items():
                span.set_attribute(f"cache.{key}", value)
            span.set_status(Status(StatusCode.OK))
            return stats

    def clear_cache(self):
        """
        Limpa o cache de embeddings.
        """
        with self.tracer.start_as_current_span(
            "embedding_service.clear_cache", kind=SpanKind.INTERNAL
        ) as span:
            previous_size = len(self._cache)
            span.set_attribute("cache.previous_size", previous_size)
            self._cache.clear()
            logger.info(
                f"Cache de embeddings limpo (tamanho anterior: {previous_size})"
            )
            update_embedding_cache_metrics("size", 0)
            update_embedding_cache_metrics("hits", self._cache_hits)
            update_embedding_cache_metrics("misses", self._cache_misses)
            update_embedding_cache_metrics("hit_ratio", 0.0)
            span.set_attribute("cache.new_size", 0)
            span.set_status(Status(StatusCode.OK))
