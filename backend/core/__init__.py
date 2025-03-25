"""
Camada de negócio central da aplicação CTA Value Tech.

Este módulo contém a lógica de negócio principal da aplicação,
independente da camada de API ou banco de dados.
"""

from .config import get_settings
from .services.embedding_service import get_embedding_service
from .services.llm_service import get_llm_service
from .services.rag_service import get_rag_service
from .services.document_service import get_document_service

__all__ = [
    'get_settings',
    'get_embedding_service',
    'get_llm_service',
    'get_rag_service',
    'get_document_service'
]