"""
Métricas específicas para o sistema RAG.
"""
from prometheus_client import Counter, Histogram, Gauge, Summary
import logging

logger = logging.getLogger(__name__)

# Métricas de desempenho do RAG
RAG_RELEVANCE_SCORE = Histogram(
    'rag_relevance_score',
    'Pontuações de relevância dos documentos recuperados',
    ['source_type'],  # Ex: 'vector', 'text', 'combined'
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
)

RAG_TOKENS_PROCESSED = Counter(
    'rag_tokens_processed_total',
    'Total de tokens processados pelo sistema RAG',
    ['stage']  # Ex: 'query', 'context', 'response'
)

RAG_DOCUMENTS_RETRIEVED = Histogram(
    'rag_documents_retrieved',
    'Número de documentos recuperados por consulta',
    buckets=(1, 2, 3, 4, 5, 10, 15, 20, 25, 30)
)

RAG_RESPONSE_TOKENS = Histogram(
    'rag_response_tokens',
    'Número de tokens nas respostas geradas',
    buckets=(10, 25, 50, 75, 100, 150, 200, 300, 400, 500, 750, 1000)
)

# Métricas de cache
CACHE_SIZE = Gauge(
    'rag_cache_size',
    'Tamanho atual do cache',
    ['cache_type']  # Ex: 'embedding', 'response'
)

CACHE_HIT_RATIO = Gauge(
    'rag_cache_hit_ratio',
    'Taxa de acertos do cache',
    ['cache_type']  # Ex: 'embedding', 'response'
)

# Métricas de qualidade
RAG_RESPONSE_QUALITY = Counter(
    'rag_response_quality',
    'Avaliação da qualidade das respostas (feedback do usuário)',
    ['rating']  # Ex: 'positive', 'negative'
)

# Métricas de erro
RAG_ERRORS = Counter(
    'rag_errors_total',
    'Erros ocorridos durante o processamento RAG',
    ['component', 'error_type']  # Ex: 'embedding', 'database', 'llm', 'processing'
)

def record_relevance_score(score: float, source_type: str = 'combined'):
    """
    Registra uma pontuação de relevância.
    
    Args:
        score: Pontuação de relevância (0.0 - 1.0)
        source_type: Tipo de fonte ('vector', 'text', 'combined')
    """
    RAG_RELEVANCE_SCORE.labels(source_type=source_type).observe(score)

def record_tokens_processed(count: int, stage: str):
    """
    Registra tokens processados em uma etapa específica.
    
    Args:
        count: Número de tokens
        stage: Etapa ('query', 'context', 'response')
    """
    RAG_TOKENS_PROCESSED.labels(stage=stage).inc(count)

def record_documents_retrieved(count: int):
    """
    Registra o número de documentos recuperados.
    
    Args:
        count: Número de documentos
    """
    RAG_DOCUMENTS_RETRIEVED.observe(count)

def record_response_tokens(count: int):
    """
    Registra o número de tokens na resposta.
    
    Args:
        count: Número de tokens na resposta
    """
    RAG_RESPONSE_TOKENS.observe(count)

def update_cache_metrics(size: int, hit_ratio: float, cache_type: str):
    """
    Atualiza métricas de cache.
    
    Args:
        size: Tamanho atual do cache
        hit_ratio: Taxa de acertos (0.0 - 1.0)
        cache_type: Tipo de cache ('embedding', 'response')
    """
    CACHE_SIZE.labels(cache_type=cache_type).set(size)
    CACHE_HIT_RATIO.labels(cache_type=cache_type).set(hit_ratio)

def record_response_feedback(is_positive: bool):
    """
    Registra feedback do usuário sobre a resposta.
    
    Args:
        is_positive: True se o feedback for positivo, False se negativo
    """
    rating = 'positive' if is_positive else 'negative'
    RAG_RESPONSE_QUALITY.labels(rating=rating).inc()

def record_error(component: str, error_type: str):
    """
    Registra um erro em um componente.
    
    Args:
        component: Componente onde ocorreu o erro
        error_type: Tipo de erro
    """
    RAG_ERRORS.labels(component=component, error_type=error_type).inc()