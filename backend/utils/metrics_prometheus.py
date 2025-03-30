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
import psutil

logger = logging.getLogger(__name__)

# --- MÉTRICAS DE INFRAESTRUTURA ---

# Contadores de requisições HTTP
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

# ERROR_RATE
ERROR_RATE =Gauge(
    'error_rate_percent',
    'Percentual de requisições com erro',
    ['endpoint']
)

# Gauge para recursos do sistema (estes valores podem subir e descer)
MEMORY_USAGE = Gauge(
    'memory_usage_bytes', 
    'Uso de memória em bytes'
)

CPU_USAGE = Gauge(
    'cpu_usage_percent',
    'Uso de CPU em porcentagem'
)

# Throughput - número de requisições por minuto
THROUGHPUT = Gauge(
    'throughput_requests_per_minute', 
    'Número de requisições por minuto'
)


# --- MÉTRICAS DE PROCESSAMENTO DE DOCUMENTOS ---

# Métricas para processamento de documentos
DOCUMENT_PROCESSING_COUNT = Counter(
    'document_processing_total',
    'Total de documentos processados',
    ['status', 'file_type'] # sucess/error, pdf/text/...
)

CHUNK_SIZE_DISTRIBUTION = Histogram(
    'document_chunk_size',
    'Distribuição de tamanhos de chunks',
    ['type'], # chars, tokens, etc
    buckets=(50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000)
)

CHUNKING_QUALITY_METRICS = Histogram(
    'chunking_quality_metrics',
    'Métricas de qualidade do chunking',
    ['strategy', 'file_type'],
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
)

# --- MÉTRICAS DE RECUPERAÇÃO ---

# Distribuição de scores (apenas histograma, não tempo)
RETRIEVAL_SCORE_DISTRIBUTION = Histogram(
    'retrieval_score_distribution',
    'Distribuição de scores de similaridade',
    ['method'],  # 'vector', 'text', 'hybrid'
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
)

# Impacto do threshold
THRESHOLD_FILTERING_COUNTER = Counter(
    'threshold_filtering_total',
    'Contagem de documentos retidos/filtrados pelo threshold',
    ['action']  # 'retained', 'filtered'
)


# --- INFORMAÇÕES DA APLICAÇÃO ---

# Informações sobre a aplicação
APP_INFO = Info('app_info', 'Informações sobre a aplicação')

T = TypeVar('T')

# --- FUNÇÕES AUXILIARES ---


def update_system_metrics():
    """
    Atualiza métricas do sistema (CPU, memória).
    Esta função deve ser chamada periodicamente.
    """
    
    try:
        # Atualizar uso de memória
        memory_usage = psutil.Process().memory_info().rss  # em bytes
        MEMORY_USAGE.set(memory_usage)
    
        # Atualizar uso de CPU
        cpu_percent = psutil.Process().cpu_percent(interval=0.1)
        CPU_USAGE.set(cpu_percent)
        
    except Exception as e:
        logger.error(f"Erro ao atualizar métricas do sistema: {e}")


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