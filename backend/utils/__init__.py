"""
Utilitários compartilhados para a aplicação CTA Value Tech.
"""

from .logging import configure_logging, get_logger
from .validation import validate_text, validate_file_type, validate_query
from .metrics import track_timing
from .telemetry import setup_telemetry, get_tracer
from .metrics_prometheus import (
    update_system_metrics,
    init_app_info,
    create_metrics_app,
    record_embedding_time,
    update_embedding_cache_metrics,
    record_llm_time,
    record_tokens,
    record_document_processing,
    record_chunk_size,
    record_extraction_time,
    record_user_feedback,
    record_retrieval_score,
    record_documents_retrieved,
    record_threshold_filtering,
    record_retrieval_time,
    record_chunking_quality,
    record_llm_error,
)

__all__ = [
    # Logging
    "configure_logging",
    "get_logger",
    # Validação
    "validate_text",
    "validate_file_type",
    "validate_query",
    # Métricas básicas
    "track_timing",
    # Telemetria
    "setup_telemetry",
    "get_tracer",
    # Métricas Prometheus
    "update_system_metrics",
    "init_app_info",
    "create_metrics_app",
    "record_embedding_time",
    "update_embedding_cache_metrics",
    "record_llm_time",
    "record_tokens",
    "record_document_processing",
    "record_chunk_size",
    "record_extraction_time",
    "record_user_feedback",
    "record_retrieval_score",
    "record_documents_retrieved",
    "record_threshold_filtering",
    "record_retrieval_time",
    "record_chunking_quality",
    "record_llm_error",
]
