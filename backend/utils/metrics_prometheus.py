"""
Utilitários para métricas do Prometheus.
"""
import time
from prometheus_client import Counter, Histogram, Gauge, Summary, Info
from prometheus_client import make_wsgi_app
from starlette.middleware.wsgi import WSGIMiddleware
from typing import Dict, Any, Callable, TypeVar, cast
import logging
import functools

logger = logging.getLogger(__name__)

# Definir métricas
# Contadores - incrementam apenas
HTTP_REQUESTS_TOTAL = Counter(
    'http_requests_total', 
    'Total de requisições HTTP', 
    ['method', 'endpoint', 'status']
)

# Histograma - para latência de requisições
REQUEST_LATENCY = Histogram(
    'request_latency_seconds', 
    'Latência das requisições HTTP',
    ['method', 'endpoint'],
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, 25.0, 50.0, 75.0, 100.0)
)

# Contador para operações RAG
RAG_OPERATIONS = Counter(
    'rag_operations_total',
    'Operações do RAG',
    ['operation']
)

# Histograma para tempos de etapas RAG
RAG_PROCESSING_TIME = Histogram(
    'rag_processing_time_seconds',
    'Tempo de processamento para operações RAG',
    ['stage'],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)
)

# Contador para embeddings
EMBEDDING_OPERATIONS = Counter(
    'embedding_operations_total',
    'Operações de embedding',
    ['operation']
)

LLM_PROCESSING_TIME = Histogram(
    'llm_processing_time_seconds',
    'Tempo de processamento para operações do LLM',
    ['operation'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 7.5, 10.0, 15.0, 30.0, 60.0)
)

# Gauge para recursos do sistema (estes valores podem subir e descer)
MEMORY_USAGE = Gauge('memory_usage_bytes', 'Uso de memória em bytes')
CPU_USAGE = Gauge('cpu_usage_percent', 'Uso de CPU em porcentagem')

# Informações sobre a aplicação
APP_INFO = Info('app_info', 'Informações sobre a aplicação')

T = TypeVar('T')

def track_time_prometheus(histogram: Histogram, labels: Dict[str, str] = None):
    """
    Decorator para medir o tempo de execução de uma função com Prometheus.
    
    Args:
        histogram: Histograma do Prometheus para registrar o tempo
        labels: Labels a serem aplicados ao histograma
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if labels:
                histogram_with_labels = histogram.labels(**labels)
            else:
                histogram_with_labels = histogram
                
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.time()
                execution_time = end_time - start_time
                histogram_with_labels.observe(execution_time)
                
        return cast(Callable[..., T], wrapper)
    return decorator

def update_system_metrics():
    """
    Atualiza métricas do sistema (CPU, memória).
    Esta função deve ser chamada periodicamente.
    """
    import psutil
    
    # Atualizar uso de memória
    memory_usage = psutil.Process().memory_info().rss  # em bytes
    MEMORY_USAGE.set(memory_usage)
    
    # Atualizar uso de CPU
    cpu_percent = psutil.Process().cpu_percent(interval=0.1)
    CPU_USAGE.set(cpu_percent)

def init_app_info(app_name: str, app_version: str):
    """
    Inicializa informações sobre a aplicação.
    
    Args:
        app_name: Nome da aplicação
        app_version: Versão da aplicação
    """
    APP_INFO.info({'name': app_name, 'version': app_version})

def create_metrics_app():
    """
    Cria um aplicativo WSGI para expor métricas do Prometheus.
    
    Returns:
        WSGIMiddleware: Middleware para expor métricas
    """
    return WSGIMiddleware(make_wsgi_app())