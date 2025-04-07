# debug/metrics_prometheus.py

"""
Utilitários para métricas do Prometheus.
(Arquivo consolidado incluindo métricas de infraestrutura, processamento, RAG e auxiliares)
"""
import time
from prometheus_client import Counter, Histogram, Gauge, Summary, Info
from prometheus_client import make_wsgi_app
from starlette.middleware.wsgi import WSGIMiddleware
import logging
import psutil
from typing import TypeVar  # Adicionado para T = TypeVar('T')

logger = logging.getLogger(__name__)

# --- MÉTRICAS DE INFRAESTRUTURA ---

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total", "Total de requisições HTTP", ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "request_latency_seconds",
    "Latência das requisições HTTP",
    ["method", "endpoint"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),  # Buckets ajustados para web
)

ERROR_RATE = Gauge(
    "error_rate_percent",
    "Percentual de requisições com erro nos últimos X minutos",  # Descrição ajustada
    ["endpoint"],
)

MEMORY_USAGE = Gauge("memory_usage_bytes", "Uso de memória em bytes")

CPU_USAGE = Gauge("cpu_usage_percent", "Uso de CPU em porcentagem")

THROUGHPUT = Gauge(
    "throughput_requests_per_minute",
    "Número de requisições por minuto (calculado sobre um período)",  # Descrição ajustada
)

# --- MÉTRICAS DE PROCESSAMENTO DE DOCUMENTOS ---

DOCUMENT_PROCESSING_COUNT = Counter(
    "document_processing_total",
    "Total de documentos processados",
    ["status", "file_type"],  # success/error, pdf/text/...
)

CHUNK_SIZE_DISTRIBUTION = Histogram(
    "document_chunk_size_distribution",  # Nome ajustado para clareza
    "Distribuição de tamanhos de chunks",
    ["type"],  # chars, tokens, etc
    buckets=(50, 100, 200, 300, 400, 500, 750, 1000, 1500, 2000),  # Buckets ajustados
)

EXTRACTION_TIME = Histogram(
    "document_extraction_seconds",
    "Tempo para extrair texto dos documentos",
    ["file_type"],  # pdf, text, etc
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0),  # Buckets ajustados
)

CHUNKING_QUALITY_METRICS = Histogram(
    "chunking_quality_score",  # Nome ajustado para indicar score
    "Distribuição dos scores de qualidade do chunking (ex: coerência)",
    ["strategy", "file_type"],
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)

# --- MÉTRICAS DE EMBEDDING ---

EMBEDDING_GENERATION_TIME = Histogram(
    "embedding_generation_seconds",
    "Tempo para gerar embeddings",
    ["operation_type"],  # single, batch # Label renomeado de batch_size
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

EMBEDDING_CACHE_METRICS = Gauge(
    "embedding_cache_metrics",
    "Métricas do cache de embeddings",
    ["metric_type"],  # size, hits, misses, hit_ratio
)

# --- MÉTRICAS DE RECUPERAÇÃO (RAG - Movidas de rag_metrics.py) ---

RETRIEVAL_SCORE_DISTRIBUTION = Histogram(
    "rag_retrieval_score_distribution",
    "Distribuição de scores de similaridade/relevância na recuperação",  # Descrição ajustada
    ["method"],  # 'vector', 'text', 'hybrid', 'reranked' # Opções de label expandidas
    buckets=(0.1, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),  # Buckets ajustados
)

RETRIEVAL_TIME = Histogram(
    "rag_retrieval_time_seconds",
    "Tempo gasto em cada fase do processo de recuperação",
    ["phase"],  # 'vector', 'text', 'hybrid', 'process', 'rerank', 'total'
    buckets=(
        0.001,
        0.005,
        0.01,
        0.05,
        0.1,
        0.5,
        1.0,
        2.0,
        5.0,
    ),  # Buckets para tempos menores
)

DOCUMENTS_RETRIEVED = Histogram(
    "rag_documents_retrieved_count",  # Nome ajustado para clareza
    "Distribuição do número de documentos recuperados por consulta (antes do limite final)",  # Descrição ajustada
    buckets=(1, 3, 5, 10, 15, 20, 30, 50),  # Buckets ajustados
)

THRESHOLD_FILTERING_COUNTER = Counter(
    "rag_threshold_filtering_total",
    "Contagem de documentos retidos/filtrados pelo threshold de relevância",
    ["action"],  # 'retained', 'filtered'
)

# --- MÉTRICAS DE GERAÇÃO (LLM) ---

LLM_GENERATION_TIME = Histogram(
    "llm_generation_seconds",
    "Tempo para geração de texto pelo LLM",
    ["model"],  # Ex: meta/llama3-70b-instruct
    buckets=(
        0.1,
        0.5,
        1.0,
        2.0,
        3.0,
        5.0,
        7.5,
        10.0,
        15.0,
        20.0,
        30.0,
    ),  # Buckets ajustados
)

LLM_TOKENS = Histogram(
    "llm_tokens_count",  # Nome ajustado
    "Distribuição do número de tokens utilizados na interação com LLM",  # Descrição ajustada
    ["type"],  # input, output
    buckets=(
        50,
        100,
        250,
        500,
        1000,
        1500,
        2000,
        3000,
        4000,
        5000,
        8000,
    ),  # Buckets ajustados
)

LLM_ERRORS_TOTAL = Counter(
    "llm_errors_total",
    "Total de erros durante a geração de texto pelo LLM",
    ["model"],  # Label para saber qual modelo falhou
)

# --- MÉTRICAS DE FEEDBACK ---

USER_FEEDBACK = Counter(
    "user_feedback_total",
    "Feedback do usuário sobre as respostas",
    ["rating"],  # positive, negative
)

# --- INFORMAÇÕES DA APLICAÇÃO ---

APP_INFO = Info("app_info", "Informações sobre a aplicação")

T = TypeVar("T")  # Definindo T

# --- FUNÇÕES AUXILIARES ---


def update_system_metrics():
    """
    Atualiza métricas do sistema (CPU, memória).
    Esta função deve ser chamada periodicamente ou a cada requisição.
    """
    try:
        process = psutil.Process()
        # Atualizar uso de memória
        memory_info = process.memory_info()
        MEMORY_USAGE.set(memory_info.rss)  # RSS: Resident Set Size

        # Atualizar uso de CPU
        # Usar cpu_percent(interval=None) para obter desde a última chamada é mais eficiente em middlewares
        cpu_percent = process.cpu_percent(interval=None)
        # Primeira chamada retorna 0.0, chamadas subsequentes o % desde a última.
        # Se chamado com intervalo muito curto pode subestimar picos. Chamar a cada req pode ser ok.
        if (
            cpu_percent is not None
        ):  # Ignorar a primeira chamada potencialmente 0.0 ou None
            CPU_USAGE.set(cpu_percent)

    except Exception as e:
        logger.error(f"Erro ao atualizar métricas do sistema: {e}")


def init_app_info(app_name: str, app_version: str):
    """
    Inicializa informações sobre a aplicação.
    """
    APP_INFO.info({"name": app_name, "version": app_version})


def create_metrics_app():
    """
    Cria um aplicativo WSGI para expor métricas do Prometheus.
    """
    return WSGIMiddleware(make_wsgi_app())


# --- Funções de Registro Específicas ---


def record_embedding_time(seconds: float, operation_type: str):  # Parâmetro renomeado
    """
    Registra tempo de geração de embeddings.
    """
    EMBEDDING_GENERATION_TIME.labels(
        operation_type=operation_type  # Label renomeado
    ).observe(seconds)


def update_embedding_cache_metrics(metric_type: str, value: float):
    """
    Atualiza métricas do cache de embeddings.
    """
    EMBEDDING_CACHE_METRICS.labels(metric_type=metric_type).set(value)


def record_llm_time(seconds: float, model: str):
    """
    Registra tempo de geração do LLM.
    """
    LLM_GENERATION_TIME.labels(model=model).observe(seconds)


def record_tokens(count: int, type_name: str):
    """
    Registra número de tokens.
    """
    LLM_TOKENS.labels(type=type_name).observe(count)


def record_document_processing(status: str, file_type: str):
    """
    Registra processamento de documento.
    """
    DOCUMENT_PROCESSING_COUNT.labels(status=status, file_type=file_type).inc()


def record_chunk_size(size: int, type_name: str = "chars"):
    """
    Registra tamanho de chunk.
    """
    CHUNK_SIZE_DISTRIBUTION.labels(type=type_name).observe(size)


def record_extraction_time(seconds: float, file_type: str):
    """
    Registra tempo de extração de texto.
    """
    EXTRACTION_TIME.labels(file_type=file_type).observe(seconds)


def record_user_feedback(rating: str):
    """
    Registra feedback do usuário.
    """
    USER_FEEDBACK.labels(rating=rating).inc()


# Funções movidas de rag_metrics.py
def record_retrieval_score(score: float, method: str):
    """Registra um score de recuperação."""
    RETRIEVAL_SCORE_DISTRIBUTION.labels(method=method).observe(score)


def record_documents_retrieved(count: int):
    """Registra o número de documentos recuperados."""
    DOCUMENTS_RETRIEVED.observe(count)  # Histogram não usa .labels aqui


def record_threshold_filtering(action: str, count: int = 1):
    """Registra a ação do threshold (retenção ou filtragem)."""
    THRESHOLD_FILTERING_COUNTER.labels(action=action).inc(count)


# Nova função para registrar tempo de recuperação
def record_retrieval_time(seconds: float, phase: str):
    """Registra o tempo gasto em uma fase do processo de recuperação."""
    RETRIEVAL_TIME.labels(phase=phase).observe(seconds)


# Função para registrar qualidade do chunking (associada a CHUNKING_QUALITY_METRICS)
def record_chunking_quality(score: float, strategy: str, file_type: str):
    """Registra o score de qualidade do chunking."""
    CHUNKING_QUALITY_METRICS.labels(strategy=strategy, file_type=file_type).observe(
        score
    )


def record_llm_error(model: str):
    """Registra um erro ocorrido na chamada ao LLM."""
    LLM_ERRORS_TOTAL.labels(model=model).inc()
