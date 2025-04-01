"""
Serviço para geração e manipulação de embeddings.
"""
import time
import logging
from typing import List, Dict, Any, Optional
from langchain_huggingface import HuggingFaceEmbeddings
from core.config import get_settings
from processors.normalizers.text_normalizer import clean_text_for_embedding
from opentelemetry import trace
from utils.telemetry import get_tracer
from utils.metrics_prometheus import record_embedding_time, update_embedding_cache_metrics
from opentelemetry.trace import SpanKind, Status, StatusCode

logger = logging.getLogger(__name__)

settings = get_settings()

class EmbeddingService:
    """
    Serviço para geração de embeddings para textos.
    
    Responsável por:
    - Inicializar e gerenciar modelos de embedding
    - Gerar embeddings para textos e consultas
    - Implementar cache para embeddings frequentes
    - Fornecer métricas e logging
    """
    
    def __init__(self):
        """
        Inicializa o serviço de embeddings.
        """
        with get_tracer(__name__).start_as_current_span("embedding_service.__init__") as init_span:
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
            "embedding_service.initialize_model",
             kind=SpanKind.INTERNAL
        ) as span:
            try:
                model_name = self.settings.EMBEDDING_MODEL
                device = "cpu"
                span.set_attribute("model.device", device)
                span.set_attribute("model.name", model_name)

                logger.info(f"Inicializando modelo de embeddings: {model_name} no dispositivo: {device}")

                model_init_start = time.time()
                self.model = HuggingFaceEmbeddings(
                    model_name=model_name,
                    model_kwargs={"device": device},
                    encode_kwargs={"normalize_embeddings": True}
                )
                model_init_duration = time.time() - model_init_start
                span.set_attribute("model.initialization_time_ms", int(model_init_duration * 1000))

                test_text = "verificação de dimensão"
                with self.tracer.start_as_current_span("embedding_service.initialize_model.dimension_check") as check_span:
                    test_embedding = self.model.embed_query(test_text)
                    embedding_dim = len(test_embedding)
                    check_span.set_attribute("embedding.dimension", embedding_dim)

                span.set_attribute("model.dimension", embedding_dim)
                configured_dim = self.settings.EMBEDDING_DIMENSION
                span.set_attribute("model.configured_dimension", configured_dim)

                if embedding_dim != configured_dim:
                    warning_msg = f"Dimensão do embedding ({embedding_dim}) difere da configurada ({configured_dim})"
                    logger.warning(warning_msg)
                    span.set_attribute("model.dimension_mismatch", True)

                logger.info(f"Modelo de embeddings '{model_name}' inicializado. Dimensão: {embedding_dim}. Tempo: {model_init_duration:.2f}s")
                span.set_status(Status(StatusCode.OK))

            except Exception as e:
                logger.error(f"Falha crítica ao inicializar modelo de embeddings '{model_name}': {e}", exc_info=True)
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, description=str(e)))
                span.set_attribute("error.type", type(e).__name__)
                raise RuntimeError(f"Falha ao inicializar modelo de embeddings: {e}") from e
    
    def embed_text(self, text: str) -> List[float]:
        """
        Gera embedding para um texto único.
        
        Args:
            text: Texto para gerar embedding
            
        Returns:
            list: Vetor de embedding
        """
        with self.tracer.start_as_current_span(
            "embedding_service.embed_text",
            kind=SpanKind.INTERNAL
        ) as span:
            start_time = time.time()

            span.set_attribute("vector.text_length", len(text))
            span.set_attribute("model.name", self.settings.EMBEDDING_MODEL)

            if not text or not text.strip():
                logger.warning("Tentativa de embedding para texto vazio.")
                span.set_attribute("vector.text_empty", True)
                span.set_status(Status(StatusCode.OK, "Texto vazio, retornando vetor zero."))
                return [0.0] * self.settings.EMBEDDING_DIMENSION

            clean_text = clean_text_for_embedding(text).lower()
            span.set_attribute("vector.cleaned_text_length", len(clean_text))

            cache_key = hash(clean_text)
            cached_embedding = self._cache.get(cache_key)

            if cached_embedding is not None:
                self._cache_hits += 1
                span.set_attribute("cache.hit", True)
                update_embedding_cache_metrics('hits', self._cache_hits)
                hit_ratio = self._cache_hits / max(1, self._cache_hits + self._cache_misses)
                update_embedding_cache_metrics('hit_ratio', hit_ratio)
                span.set_attribute("cache.hit_ratio", hit_ratio)

                elapsed_time = time.time() - start_time
                record_embedding_time(elapsed_time, operation_type='single')
                span.set_attribute("duration_ms", int(elapsed_time * 1000))
                span.set_attribute("vector.dimension", len(cached_embedding))
                span.set_status(Status(StatusCode.OK))
                return cached_embedding

            span.set_attribute("cache.hit", False)
            self._cache_misses += 1
            update_embedding_cache_metrics('misses', self._cache_misses)
            hit_ratio = self._cache_hits / max(1, self._cache_hits + self._cache_misses)
            update_embedding_cache_metrics('hit_ratio', hit_ratio)
            span.set_attribute("cache.hit_ratio", hit_ratio)

            try:
                with self.tracer.start_as_current_span("embedding_service.model_inference") as model_span:
                    model_start_time = time.time()
                    embedding = self.model.embed_query(clean_text)
                    model_elapsed_time = time.time() - model_start_time

                    model_span.set_attribute("duration_ms", int(model_elapsed_time * 1000))
                    model_span.set_attribute("vector.dimension", len(embedding))
                    model_span.set_status(Status(StatusCode.OK))

                self._total_embeddings += 1

                if len(self._cache) < 10000:
                    self._cache[cache_key] = embedding
                    update_embedding_cache_metrics('size', len(self._cache))
                    span.set_attribute("cache.updated", True)
                else:
                     span.set_attribute("cache.full", True)

                elapsed_time = time.time() - start_time
                record_embedding_time(elapsed_time, operation_type='single')
                span.set_attribute("duration_ms", int(elapsed_time * 1000))
                span.set_attribute("vector.dimension", len(embedding))
                span.set_status(Status(StatusCode.OK))
                return embedding

            except Exception as e:
                elapsed_time = time.time() - start_time
                record_embedding_time(elapsed_time, operation_type='single')
                logger.error(f"Erro ao gerar embedding para texto: '{clean_text[:50]}...': {e}", exc_info=True)
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, description=str(e)))
                span.set_attribute("error.type", type(e).__name__)
                return [0.0] * self.settings.EMBEDDING_DIMENSION
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Gera embeddings para múltiplos textos em lote.
        
        Args:
            texts: Lista de textos para gerar embeddings
            
        Returns:
            list: Lista de vetores de embedding
        """
        with self.tracer.start_as_current_span(
            "embedding_service.embed_batch",
            kind=SpanKind.INTERNAL
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

            avg_len = sum(len(t) for t in clean_texts_map.keys()) / max(1, len(clean_texts_map))
            span.set_attribute("vector.unique_texts_count", len(clean_texts_map))
            span.set_attribute("vector.avg_unique_text_length", avg_len)

            embeddings: List[Optional[List[float]]] = [None] * batch_size
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
                        embeddings[i] = cached_embedding
                else:
                    texts_to_embed_list.append(clean_text)

            if cache_hits_in_batch > 0:
                 update_embedding_cache_metrics('hits', self._cache_hits)

            uncached_count = len(texts_to_embed_list)
            span.set_attribute("cache.batch_hits_count", cache_hits_in_batch)
            span.set_attribute("cache.batch_unique_misses_count", uncached_count)

            if uncached_count > 0:
                self._cache_misses += uncached_count
                span.set_attribute("cache.misses_increment", uncached_count)
                update_embedding_cache_metrics('misses', self._cache_misses)

                try:
                    with self.tracer.start_as_current_span("embedding_service.model_batch_inference") as model_span:
                        model_start_time = time.time()
                        new_embeddings = self.model.embed_documents(texts_to_embed_list)
                        model_elapsed_time = time.time() - model_start_time

                        model_span.set_attribute("duration_ms", int(model_elapsed_time * 1000))
                        model_span.set_attribute("vector.batch_size", uncached_count)
                        if new_embeddings:
                            model_span.set_attribute("vector.dimension", len(new_embeddings[0]))
                        model_span.set_status(Status(StatusCode.OK))

                    self._total_embeddings += uncached_count

                    cache_updated = False
                    if len(self._cache) < 10000:
                        space_available = 10000 - len(self._cache)
                        can_add_count = min(space_available, len(new_embeddings))
                        for i in range(can_add_count):
                            clean_text = texts_to_embed_list[i]
                            embedding = new_embeddings[i]
                            cache_key = hash(clean_text)
                            self._cache[cache_key] = embedding
                            cache_updated = True
                        span.set_attribute("cache.added_count", can_add_count)
                        if can_add_count < len(new_embeddings):
                            span.set_attribute("cache.full", True)

                    for i, embedding in enumerate(new_embeddings):
                         clean_text = texts_to_embed_list[i]
                         for original_index in clean_texts_map[clean_text]:
                              embeddings[original_index] = embedding

                    if cache_updated:
                        update_embedding_cache_metrics('size', len(self._cache))

                except Exception as e:
                    logger.error(f"Erro ao gerar embeddings em lote para {uncached_count} textos: {e}", exc_info=True)
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, description=str(e)))
                    span.set_attribute("error.type", type(e).__name__)
                    zero_vec = [0.0] * self.settings.EMBEDDING_DIMENSION
                    for text_to_embed in texts_to_embed_list:
                        for original_index in clean_texts_map[text_to_embed]:
                             if embeddings[original_index] is None:
                                embeddings[original_index] = zero_vec

            final_embeddings: List[List[float]] = []
            zero_vec = [0.0] * self.settings.EMBEDDING_DIMENSION
            for emb in embeddings:
                final_embeddings.append(emb if emb is not None else zero_vec)

            hit_ratio = self._cache_hits / max(1, self._cache_hits + self._cache_misses)
            update_embedding_cache_metrics('hit_ratio', hit_ratio)
            span.set_attribute("cache.hit_ratio", hit_ratio)

            elapsed_time = time.time() - start_time
            record_embedding_time(elapsed_time, operation_type='batch')
            span.set_attribute("duration_ms", int(elapsed_time * 1000))
            if final_embeddings:
                 span.set_attribute("vector.dimension", len(final_embeddings[0]))
            if span.status.status_code != StatusCode.ERROR:
                 span.set_status(Status(StatusCode.OK))

            return final_embeddings
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do cache de embeddings.
        
        Returns:
            dict: Estatísticas do cache
        """
        with self.tracer.start_as_current_span("embedding_service.get_cache_stats") as span:
            total_requests = self._cache_hits + self._cache_misses
            hit_rate = self._cache_hits / max(1, total_requests) if total_requests > 0 else 0.0

            update_embedding_cache_metrics('size', len(self._cache))
            update_embedding_cache_metrics('hits', self._cache_hits)
            update_embedding_cache_metrics('misses', self._cache_misses)
            update_embedding_cache_metrics('hit_ratio', hit_rate)

            stats = {
                "cache_size": len(self._cache),
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "hit_rate": hit_rate,
                "total_embeddings_generated": self._total_embeddings
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
            "embedding_service.clear_cache",
             kind=SpanKind.INTERNAL
        ) as span:
            previous_size = len(self._cache)
            span.set_attribute("cache.previous_size", previous_size)
            self._cache.clear()
            logger.info(f"Cache de embeddings limpo (tamanho anterior: {previous_size})")
            update_embedding_cache_metrics('size', 0)
            update_embedding_cache_metrics('hits', self._cache_hits)
            update_embedding_cache_metrics('misses', self._cache_misses)
            update_embedding_cache_metrics('hit_ratio', 0.0)
            span.set_attribute("cache.new_size", 0)
            span.set_status(Status(StatusCode.OK))

# Instância singleton para uso em toda a aplicação
_embedding_service_instance: Optional[EmbeddingService] = None

def get_embedding_service() -> EmbeddingService:
    """
    Retorna a instância do serviço de embeddings.
    
    Returns:
        EmbeddingService: Instância do serviço
    """
    global _embedding_service_instance
    
    if _embedding_service_instance is None:
        _embedding_service_instance = EmbeddingService()
    
    return _embedding_service_instance