"""
Módulo de configurações da aplicação RAG.
Exporta todas as configurações necessárias para o funcionamento da aplicação.
"""

from .settings import (
    EMBEDDING_MODEL,
    DOCUMENT_PROCESSING,
    DATABASE,
    DIRECTORIES
)

from .environment import (
    DB_CONFIG,
    API_CONFIG,
    validate_environment
)

__all__ = [
    'EMBEDDING_MODEL',
    'DOCUMENT_PROCESSING',
    'DATABASE',
    'DIRECTORIES',
    'DB_CONFIG',
    'API_CONFIG',
    'validate_environment'
] 