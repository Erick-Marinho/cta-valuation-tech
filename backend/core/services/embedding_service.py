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
        self.settings = get_settings()
        self._cache = {}  # Cache simples para embeddings frequentes
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_embeddings = 0
        self.tracer = get_tracer(__name__)
        self._initialize_model()
        
    def _initialize_model(self):
        """
        Inicializa o modelo de embeddings.
        """
        try:
            model_name = self.settings.EMBEDDING_MODEL
            # device = "cuda" if self.settings.DEBUG else "cpu"
            device = "cpu"
            
            logger.info(f"Inicializando modelo de embeddings {model_name} no dispositivo {device}")
            
            self.model = HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={"device": device},
                encode_kwargs={"normalize_embeddings": True}
            )
            
            # Verificar a dimensão do embedding
            test_embedding = self.embed_text("teste")
            embedding_dim = len(test_embedding)
            
            if embedding_dim != self.settings.EMBEDDING_DIMENSION:
                logger.warning(
                    f"Dimensão do embedding ({embedding_dim}) é diferente da configurada "
                    f"({self.settings.EMBEDDING_DIMENSION})"
                )
            
            logger.info(f"Modelo de embeddings inicializado com sucesso. Dimensão: {embedding_dim}")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar modelo de embeddings: {e}")
            raise
    
    def embed_text(self, text: str) -> List[float]:
        """
        Gera embedding para um texto.
        
        Args:
            text: Texto para gerar embedding
            
        Returns:
            list: Vetor de embedding
        """
        
        # Iniciar temporizador para métrica Prometheus
        start_time = time.time()
        
        # Criar um span para rastrear esta operação
        with self.tracer.start_as_current_span("embed_text") as span:
            # Adicionar atributos ao span para facilitar análise
            span.set_attribute("text.length", len(text))
        
            if not text or not text.strip():
                logger.warning(f"Tentativa de embedding para texto vazio ou apenas espaços")
                # Registrar no span
                span.set_attribute("text.empty", True)
                # Retornar embedding zerado com a dimensão correta
                zero_vec = [0.0] * self.settings.EMBEDDING_DIMENSION
                return zero_vec
            
            # Limpar e normalizar o texto- garante que o texto seja convertido para minúsculas
            clean_text = clean_text_for_embedding(text).lower()
            span.set_attribute("text.cleaned_length", len(clean_text))
        
            # Verificar no cache
            cache_key = hash(clean_text)
            if cache_key in self._cache:
                self._cache_hits += 1
                span.set_attribute("cache.hit", True)
                embedding = self._cache[cache_key]
                
                # Registrar hit no cache (Prometheus)
                update_embedding_cache_metrics('hits', self._cache_hits)
                cache_misses = self._cache_misses
                update_embedding_cache_metrics('hit_ratio', 
                    self._cache_hits / max(1, self._cache_hits + self._cache_misses))
                
                # Finalizar temporizador e registrar métrica
                elapsed_time = time.time() - start_time
                record_embedding_time(elapsed_time, operation_type='single')
                
                return embedding
        
            # Caso não esteja no cache, gerar embedding
            try:
                # Registrar que não houve hit no cache
                span.set_attribute("cache.hit", False)
                self._cache_misses += 1
                self._total_embeddings += 1
                
                # Atualizar métricas Prometheus imediatamente
                update_embedding_cache_metrics('misses', self._cache_misses)
                update_embedding_cache_metrics('hit_ratio',
                    self._cache_hits / max(1, self._cache_hits + self._cache_misses))
                
                # Criar um sub-span para rastrear especificamente a operação do modelo
                with self.tracer.start_as_current_span("model_inference") as model_span:
                    model_start_time = time.time()
                    embedding = self.model.embed_query(clean_text)
                    model_elapsed_time = time.time() - model_start_time
                    model_span.set_attribute("inference_time", model_elapsed_time)
                
                # Registrar miss no cache (Prometheus)
                update_embedding_cache_metrics('misses', self._cache_misses)
                update_embedding_cache_metrics('hit_ratio', 
                    self._cache_hits / max(1, self._cache_hits + self._cache_misses))
                    
                # Adicionar ao cache se não for muito grande
                if len(self._cache) < 10000:  # Limitar tamanho do cache
                    self._cache[cache_key] = embedding
                    update_embedding_cache_metrics('size', len(self._cache))
                
                # Finalizar temporizador e registrar métrica
                elapsed_time = time.time() - start_time
                record_embedding_time(elapsed_time, operation_type='single')
                
                return embedding
                
            except Exception as e:
                # Finalizar temporizador mesmo em caso de erro
                elapsed_time = time.time() - start_time
                record_embedding_time(elapsed_time, operation_type='single')
                
                logger.error(f"Erro ao gerar embedding: {e}")
                
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, f"Erro: {e}"))
                
                # Retornar embedding zerado em caso de erro
                return [0.0] * self.settings.EMBEDDING_DIMENSION
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Gera embeddings para múltiplos textos em lote.
        
        Args:
            texts: Lista de textos para gerar embeddings
            
        Returns:
            list: Lista de vetores de embedding
        """
        
        start_time = time.time()
        
        # Criar um span para rastrear esta operação em lote
        with self.tracer.start_as_current_span("embed_batch") as span:
            span.set_attribute("batch.size", len(texts) if texts else 0)
            
            if not texts:
                return []
        
            # Limpar e normalizar os textos - garante que o texto seja convertido para minúsculas
            clean_texts = [clean_text_for_embedding(text).lower() for text in texts]
            
            # Calcular tamanho médio dos textos e registrar
            avg_text_len = sum(len(t) for t in clean_texts) / max(1, len(clean_texts))
            span.set_attribute("texts.avg_length", avg_text_len)
        
            # Verificar quais textos estão no cache
            embeddings = [None] * len(texts)
            texts_to_embed = []
            indices_to_embed = {}
            cache_hits_in_batch = 0
            cache_misses_in_batch = 0
        
            for i, text in enumerate(texts):
                clean_text = clean_text_for_embedding(text).lower()
                if not clean_text: # Lidar com textos vazios
                    embeddings[i] = [0.0] * self.settings.EMBEDDING_DIMENSION
                    continue
                
                cache_key = hash(clean_text)
                if cache_key in self._cache:
                    embeddings[i] = self._cache[cache_key]
                    self._cache_hits += 1
                    cache_hits_in_batch += 1
                else:
                    # Adicionar à lista para buscar, apenas uma vez por texto único
                    if clean_text not in indices_to_embed:
                        texts_to_embed.append(clean_text)
                        indices_to_embed[clean_text] = []
                    indices_to_embed[clean_text].append(i)
                    # Contar miss apenas uma vez por texto único no batch
                    # (O incremento global self._cache_misses será feito depois)
                    
            # Calcular misses únicos no batch
            cache_misses_in_batch = len(texts_to_embed)
            self._cache_misses += cache_misses_in_batch # Atualizar contador global

            # Atualizar métricas Prometheus para este batch (hits e misses)
            if cache_hits_in_batch > 0:
                update_embedding_cache_metrics('hits', self._cache_hits)
            if cache_misses_in_batch > 0:
                update_embedding_cache_metrics('misses', self._cache_misses)

            # Atualizar hit_ratio se houve hits ou misses neste batch
            if cache_hits_in_batch > 0 or cache_misses_in_batch > 0:
                update_embedding_cache_metrics('hit_ratio',
                    self._cache_hits / max(1, self._cache_hits + self._cache_misses))

            # ... (Registrar dados de cache no span)
            span.set_attribute("batch.cache_hits", cache_hits_in_batch)
            span.set_attribute("batch.cache_misses", cache_misses_in_batch)
        
            # Gerar embeddings para textos que não estão no cache
            if texts_to_embed:
                try:
                    # Criar um sub-span para a geração de embeddings em lote
                    with self.tracer.start_as_current_span("model_batch_inference") as batch_span:
                        batch_span.set_attribute("model.name", self.settings.EMBEDDING_MODEL)
                        batch_span.set_attribute("batch.uncached_size", len(texts_to_embed))
                        
                        new_embeddings = self.model.embed_documents(texts_to_embed)
                        
                    self._total_embeddings += len(texts_to_embed)
                    
                    # Adicionar novos embeddings ao cache
                    cache_update = False
                    for i, embedding in enumerate(new_embeddings):
                        clean_text = texts_to_embed[i]
                        cache_key = hash(clean_text)
                        if len(self._cache) < 10000:  # Limitar tamanho do cache
                            self._cache[cache_key] = embedding
                            cache_updated = True
                        # Preencher todos os índices originais que mapeiam para este texto
                        for original_index in indices_to_embed[clean_text]:
                            embeddings[original_index] = embedding
                            
                    # Atualizar métrica de tamanho do cache se ele foi modificado
                    if cache_updated:
                        update_embedding_cache_metrics('size', len(self._cache))

                    span.set_attribute("embedding.generation_success", True)                        
                    
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, f"Erro: {e}"))
                    logger.error(f"Erro ao gerar embeddings em lote: {e}")
                    # Preencher com embeddings zerados em caso de erro
                    for clean_text, original_indices in indices_to_embed.items():
                        for original_index in original_indices:
                            embeddings[original_index] = [0.0] * self.settings.EMBEDDING_DIMENSION
                        
            # Registrar dados sobre os embeddings retornados
            if embeddings:
                span.set_attribute("embedding.dimension", len(embeddings[0]))
                span.set_attribute("embedding.count", len(embeddings))
                
            elapsed_time = time.time() - start_time
            record_embedding_time(elapsed_time, operation_type='batch')
            
            return embeddings
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do cache de embeddings.
        
        Returns:
            dict: Estatísticas do cache
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / max(1, total_requests)
        
        # Atualizar métricas do cache no Prometheus
        update_embedding_cache_metrics('size', len(self._cache))
        update_embedding_cache_metrics('hits', self._cache_hits)
        update_embedding_cache_metrics('misses', self._cache_misses)
        update_embedding_cache_metrics('hit_ratio', hit_rate)
        
        return {
            "cache_size": len(self._cache),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": hit_rate,
            "total_embeddings_generated": self._total_embeddings
        }
    
    def clear_cache(self):
        """
        Limpa o cache de embeddings.
        """
        
        with self.tracer.start_as_current_span("clear_cache") as span:
            span.set_attribute("cache.previous_size", len(self._cache))
            self._cache.clear()
            logger.info("Cache de embeddings limpo")

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