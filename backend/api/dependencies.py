"""
Dependências compartilhadas entre os endpoints da API.
"""

from typing import Annotated, List, Optional
import logging
from fastapi import Depends, Header, HTTPException, Query, status
from core.config import get_settings, Settings
from core.services.document_service import get_document_service, DocumentService
from core.services.embedding_service import get_embedding_service, EmbeddingService
from core.services.llm_service import get_llm_service, LLMService
from core.services.rag_service import get_rag_service, RAGService
from db.schema import is_database_healthy

logger = logging.getLogger(__name__)


def get_app_settings() -> Settings:
    """
    Dependência para obter as configurações da aplicação.

    Returns:
        Settings: Configurações da aplicação
    """
    return get_settings()


def get_document_svc() -> DocumentService:
    """
    Dependência para obter o serviço de documentos.

    Returns:
        DocumentService: Serviço de processamento de documentos
    """
    return get_document_service()


def get_embedding_svc() -> EmbeddingService:
    """
    Dependência para obter o serviço de embeddings.

    Returns:
        EmbeddingService: Serviço de embeddings
    """
    return get_embedding_service()


def get_llm_svc() -> LLMService:
    """
    Dependência para obter o serviço de LLM.

    Returns:
        LLMService: Serviço de LLM
    """
    return get_llm_service()


def get_rag_svc() -> RAGService:
    """
    Dependência para obter o serviço RAG.

    Returns:
        RAGService: Serviço RAG
    """
    return get_rag_service()


def verify_db_health():
    """
    Dependência para verificar a saúde do banco de dados.

    Raises:
        HTTPException: Se o banco de dados não estiver saudável
    """
    if not is_database_healthy():
        logger.error("Banco de dados não está saudável")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço temporariamente indisponível. Tente novamente mais tarde.",
        )
    return True


def validate_api_key(x_api_key: Annotated[str, Header()] = None):
    """
    Dependência para validar a chave de API.

    Args:
        x_api_key: Chave de API fornecida no cabeçalho

    Raises:
        HTTPException: Se a chave de API for inválida

    Returns:
        bool: True se a chave for válida
    """
    settings = get_settings()

    # Se a API_KEY não estiver configurada, não validar
    if not hasattr(settings, "API_KEY") or not settings.API_KEY:
        return True

    if not x_api_key or x_api_key != settings.API_KEY:
        logger.warning(f"Tentativa de acesso com chave API inválida: {x_api_key}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Chave de API inválida"
        )

    return True


def common_query_parameters(
    limit: int = Query(10, ge=1, le=100, description="Número máximo de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
    sort_by: Optional[str] = Query(None, description="Campo para ordenação"),
    order: str = Query("asc", description="Ordem de classificação (asc ou desc)"),
):
    """
    Parâmetros de consulta comuns para endpoints com paginação e ordenação.

    Args:
        limit: Limite de resultados por página
        offset: Deslocamento para paginação
        sort_by: Campo para ordenação
        order: Ordem de classificação (asc ou desc)

    Returns:
        dict: Parâmetros de consulta
    """
    return {"limit": limit, "offset": offset, "sort_by": sort_by, "order": order}
