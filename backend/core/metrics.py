"""
Módulo para gerenciamento de métricas do Prometheus.
"""
from prometheus_client import Counter, Histogram, Gauge
import time

# Métricas para o RAG
RAG_QUERY_COUNTER = Counter(
    'rag_queries_total',
    'Total number of RAG queries processed',
    ['status']  # success ou error
)

RAG_QUERY_LATENCY = Histogram(
    'rag_query_duration_seconds',
    'Time spent processing RAG queries',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

RAG_CHUNKS_RETRIEVED = Histogram(
    'rag_chunks_retrieved',
    'Number of chunks retrieved per query',
    buckets=[1, 2, 3, 5, 10, 20]
)

# Métricas para Embeddings
EMBEDDING_GENERATION_COUNTER = Counter(
    'embedding_generations_total',
    'Total number of embeddings generated',
    ['type']  # query ou chunk
)

EMBEDDING_GENERATION_LATENCY = Histogram(
    'embedding_generation_duration_seconds',
    'Time spent generating embeddings',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

# Métricas para o LLM
LLM_REQUEST_COUNTER = Counter(
    'llm_requests_total',
    'Total number of LLM requests',
    ['status', 'model']
)

LLM_REQUEST_LATENCY = Histogram(
    'llm_request_duration_seconds',
    'Time spent on LLM requests',
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0]
)

LLM_TOKEN_COUNTER = Counter(
    'llm_tokens_total',
    'Total number of tokens processed',
    ['type']  # input ou output
)

# Métricas para o Cache
CACHE_OPERATIONS = Counter(
    'cache_operations_total',
    'Total number of cache operations',
    ['operation', 'status']  # hit ou miss
)

CACHE_SIZE = Gauge(
    'cache_size',
    'Current number of items in cache',
    ['type']  # embeddings ou documents
)

# Métricas para Documentos
DOCUMENT_PROCESSING_COUNTER = Counter(
    'document_processing_total',
    'Total number of documents processed',
    ['status', 'type']
)

DOCUMENT_PROCESSING_LATENCY = Histogram(
    'document_processing_duration_seconds',
    'Time spent processing documents',
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0]
)

CHUNKS_PER_DOCUMENT = Histogram(
    'chunks_per_document',
    'Number of chunks generated per document',
    buckets=[10, 20, 50, 100, 200, 500]
)

class MetricsTimer:
    """Classe auxiliar para medir tempo de execução."""
    
    def __init__(self, metric):
        self.metric = metric
        self.start_time = None
        self.duration = 0
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration = time.time() - self.start_time
        self.metric.observe(self.duration) 