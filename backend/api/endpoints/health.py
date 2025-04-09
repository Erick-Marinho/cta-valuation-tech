"""
Endpoints para monitoramento de saúde da aplicação.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, Optional, Annotated
import logging
import time
import os
import platform
import psutil
from config.config import get_settings, Settings
from shared.exceptions import ServiceUnavailableError
from application.interfaces.embedding_provider import EmbeddingProvider
from application.interfaces.llm_provider import LLMProvider
from interface.api.dependencies import get_embedding_provider, get_llm_provider, verify_db_health, SessionDep

logger = logging.getLogger(__name__)


# Modelos de dados para respostas
class HealthResponse(BaseModel):
    """Modelo para resposta de verificação de saúde."""

    status: str
    version: str
    timestamp: float
    components: Dict[str, Any]


class MetricsResponse(BaseModel):
    """Modelo para resposta com métricas de desempenho."""

    system: Dict[str, Any]
    database: Dict[str, Any]
    embedding: Dict[str, Any]
    llm: Dict[str, Any]


# Roteador para endpoints de monitoramento
router = APIRouter(prefix="/health", tags=["health"])


# Dependências Anotadas
SettingsDep = Annotated[Settings, Depends(get_settings)]
LLMProviderDep = Annotated[LLMProvider, Depends(get_llm_provider)]
EmbeddingProviderDep = Annotated[EmbeddingProvider, Depends(get_embedding_provider)]
# SessionDep já deve estar definido em dependencies.py


@router.get("/", response_model=HealthResponse)
async def health_check(
    settings: SettingsDep,
    # Injetar SessionDep para verificar o DB
    session: SessionDep,
    # Injetar LLMProvider para verificar se inicializa (não verificaremos resposta)
    llm_provider: LLMProviderDep,
    embedding_provider: EmbeddingProviderDep,
):
    """
    Verifica a saúde geral da aplicação e seus componentes.

    Returns:
        HealthResponse: Status de saúde da aplicação
    """
    start_time = time.time()
    component_status = {}
    overall_ok = True

    # 1. Verificar Banco de Dados
    try:
        await verify_db_health(session) # Usa a função de dependência que já valida
        component_status["database"] = {"status": "healthy"}
    except HTTPException as http_exc: # Captura o 503 de verify_db_health
        component_status["database"] = {"status": "unhealthy", "error": str(http_exc.detail)}
        overall_ok = False
    except Exception as db_exc:
        logger.error(f"Falha inesperada na verificação de saúde do DB: {db_exc}", exc_info=True)
        component_status["database"] = {"status": "unhealthy", "error": "Internal error checking DB"}
        overall_ok = False

    # 2. Verificar Embedding Provider (se inicializou)
    if embedding_provider:
         component_status["embedding_service"] = {"status": "healthy", "model": settings.EMBEDDING_MODEL}
    else:
         # Se a dependência falhar, FastAPI retornaria erro antes, mas adicionamos por segurança
         component_status["embedding_service"] = {"status": "unhealthy", "error": "Provider not initialized"}
         overall_ok = False

    # 3. Verificar LLM Provider (se inicializou)
    if llm_provider:
         component_status["llm_service"] = {"status": "healthy", "provider": "nvidia"} # Ou obter de settings/provider
    else:
         component_status["llm_service"] = {"status": "unhealthy", "error": "Provider not initialized"}
         overall_ok = False

    return HealthResponse(
        status="healthy" if overall_ok else "unhealthy",
        version=settings.APP_VERSION,
        timestamp=start_time,
        components=component_status,
    )


@router.get("/metrics", response_model=MetricsResponse)
async def metrics(
    embedding_provider: EmbeddingProviderDep,
    # llm_provider: LLMProviderDep, # O LLMProvider não tem get_metrics
    session: SessionDep # Para verificar DB
):
    """
    Retorna métricas de desempenho e uso da aplicação.

    Returns:
        MetricsResponse: Métricas de desempenho
    """
    try:
        process = psutil.Process(os.getpid())
        memory_usage = process.memory_info().rss / (1024 * 1024)
        system_metrics = {
            "memory_usage_mb": round(memory_usage, 2),
            "cpu_percent": process.cpu_percent(interval=0.1),
            "uptime_seconds": int(time.time() - process.create_time()),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        }

        embedding_metrics = {}
        if hasattr(embedding_provider, 'get_cache_stats'):
            try:
                embedding_metrics = embedding_provider.get_cache_stats()
            except Exception as emb_exc:
                logger.warning(f"Não foi possível obter métricas de embedding: {emb_exc}")
                embedding_metrics = {"error": "failed to get stats"}
        else:
            embedding_metrics = {"status": "stats not available"}

        # Métricas LLM (Placeholder - o provider atual não tem get_metrics)
        llm_metrics = {"status": "metrics not available from provider"}

        # Métricas DB (Verifica status)
        db_status = "unknown"
        try:
             await verify_db_health(session)
             db_status = "healthy"
        except Exception:
             db_status = "unhealthy"
        db_metrics = {"status": db_status}

        return MetricsResponse(
            system=system_metrics,
            database=db_metrics,
            embedding=embedding_metrics,
            llm=llm_metrics,
        )

    except Exception as e:
        logger.error(f"Erro ao coletar métricas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao coletar métricas: {str(e)}")


@router.get("/ping")
async def ping():
    """
    Endpoint simples para verificar se a API está respondendo.
    Útil para health checks de load balancers.

    Returns:
        dict: Resposta simples de ping
    """
    return {"status": "ok", "message": "pong"}
