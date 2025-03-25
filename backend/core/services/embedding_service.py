"""
Serviço para geração e manipulação de embeddings.
"""
import logging
from typing import List, Dict, Any, Optional
from langchain_huggingface import HuggingFaceEmbeddings
from core.config import get_settings
from processors.normalizers.text_normalizer import clean_text_for_embedding
from core.metrics import (
    EMBEDDING_GENERATION_COUNTER,
    EMBEDDING_GENERATION_LATENCY,
    CACHE_OPERATIONS,
    CACHE_SIZE,
    MetricsTimer
)

logger = logging.getLogger(__name__)

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
        self._initialize_model()
        
        # Inicializar métrica de tamanho do cache
        CACHE_SIZE.labels(type="embeddings").set(0)
        
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
        if not text or not text.strip():
            logger.warning(f"Tentativa de embedding para texto vazio ou apenas espaços")
            # Retornar embedding zerado com a dimensão correta
            return [0.0] * self.settings.EMBEDDING_DIMENSION
        
        # Limpar e normalizar o texto- garante que o texto seja convertido para minúsculas
        clean_text = clean_text_for_embedding(text)
        clean_text = clean_text.lower()
        
        # Verificar no cache
        cache_key = hash(clean_text)
        if cache_key in self._cache:
            CACHE_OPERATIONS.labels(operation="get", status="hit").inc()
            return self._cache[cache_key]
        
        # Caso não esteja no cache, gerar embedding
        CACHE_OPERATIONS.labels(operation="get", status="miss").inc()
        
        try:
            with MetricsTimer(EMBEDDING_GENERATION_LATENCY):
                embedding = self.model.embed_query(clean_text)
                EMBEDDING_GENERATION_COUNTER.labels(type="query").inc()
            
            # Adicionar ao cache se não for muito grande
            if len(self._cache) < 10000:  # Limitar tamanho do cache
                self._cache[cache_key] = embedding
                CACHE_OPERATIONS.labels(operation="set", status="success").inc()
                CACHE_SIZE.labels(type="embeddings").set(len(self._cache))
            
            return embedding
            
        except Exception as e:
            logger.error(f"Erro ao gerar embedding: {e}")
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
        if not texts:
            return []
        
        # Limpar e normalizar os textos - garante que o texto seja convertido para minúsculas
        clean_texts = [clean_text_for_embedding(text).lower() for text in texts]
        
        # Verificar quais textos estão no cache
        embeddings = []
        texts_to_embed = []
        indices_to_embed = []
        
        for i, clean_text in enumerate(clean_texts):
            cache_key = hash(clean_text)
            if cache_key in self._cache:
                embeddings.append(self._cache[cache_key])
                CACHE_OPERATIONS.labels(operation="get", status="hit").inc()
            else:
                texts_to_embed.append(clean_text)
                indices_to_embed.append(i)
                CACHE_OPERATIONS.labels(operation="get", status="miss").inc()
        
        # Gerar embeddings para textos que não estão no cache
        if texts_to_embed:
            try:
                with MetricsTimer(EMBEDDING_GENERATION_LATENCY):
                    new_embeddings = self.model.embed_documents(texts_to_embed)
                    EMBEDDING_GENERATION_COUNTER.labels(type="chunk").inc(len(texts_to_embed))
                
                # Adicionar novos embeddings ao cache
                for i, embedding in enumerate(new_embeddings):
                    clean_text = texts_to_embed[i]
                    cache_key = hash(clean_text)
                    if len(self._cache) < 10000:  # Limitar tamanho do cache
                        self._cache[cache_key] = embedding
                        CACHE_OPERATIONS.labels(operation="set", status="success").inc()
                
                # Atualizar tamanho do cache
                CACHE_SIZE.labels(type="embeddings").set(len(self._cache))
                
                # Inserir os novos embeddings na posição correta
                for i, embedding in zip(indices_to_embed, new_embeddings):
                    while len(embeddings) <= i:
                        embeddings.append(None)
                    embeddings[i] = embedding
                
            except Exception as e:
                logger.error(f"Erro ao gerar embeddings em lote: {e}")
                # Preencher com embeddings zerados em caso de erro
                for i in indices_to_embed:
                    while len(embeddings) <= i:
                        embeddings.append(None)
                    embeddings[i] = [0.0] * self.settings.EMBEDDING_DIMENSION
        
        return embeddings
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do cache de embeddings.
        
        Returns:
            dict: Estatísticas do cache
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0
        
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
        self._cache.clear()
        CACHE_SIZE.labels(type="embeddings").set(0)
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