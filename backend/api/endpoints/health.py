"""
Endpoints para monitoramento de saúde da aplicação.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any
import logging
import time
import os
import platform
import psutil
from core.config import get_settings, Settings
from db.schema import is_database_healthy
from core.services.embedding_service import get_embedding_service, EmbeddingService
from core.services.llm_service import get_llm_service, LLMService

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

@router.get("/", response_model=HealthResponse)
async def health_check(
    settings: Settings = Depends(get_settings),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    llm_service: LLMService = Depends(get_llm_service)
):
    """
    Verifica a saúde geral da aplicação e seus componentes.
    
    Returns:
        HealthResponse: Status de saúde da aplicação
    """
    # Verificar componentes
    db_healthy = is_database_healthy()
    
    # Tentar gerar um embedding de teste
    embedding_healthy = True
    try:
        _ = embedding_service.embed_text("teste de saúde")
    except Exception as e:
        logger.error(f"Erro no serviço de embeddings: {e}")
        embedding_healthy = False
    
    # Status geral baseado em todos os componentes
    overall_status = "healthy" if db_healthy and embedding_healthy else "unhealthy"
    
    return HealthResponse(
        status=overall_status,
        version=settings.APP_VERSION,
        timestamp=time.time(),
        components={
            "database": {
                "status": "healthy" if db_healthy else "unhealthy"
            },
            "embedding_service": {
                "status": "healthy" if embedding_healthy else "unhealthy",
                "model": settings.EMBEDDING_MODEL
            },
            "llm_service": {
                "status": "unknown"  # Não testamos o LLM diretamente para evitar custos
            }
        }
    )

@router.get("/metrics", response_model=MetricsResponse)
async def metrics(
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    llm_service: LLMService = Depends(get_llm_service)
):
    """
    Retorna métricas de desempenho e uso da aplicação.
    
    Returns:
        MetricsResponse: Métricas de desempenho
    """
    try:
        # Métricas do sistema
        process = psutil.Process(os.getpid())
        memory_usage = process.memory_info().rss / (1024 * 1024)  # Em MB
        
        system_metrics = {
            "memory_usage_mb": round(memory_usage, 2),
            "cpu_percent": process.cpu_percent(interval=0.1),
            "uptime_seconds": int(time.time() - process.create_time()),
            "python_version": platform.python_version(),
            "platform": platform.platform()
        }
        
        # Métricas de embedding
        embedding_metrics = embedding_service.get_cache_stats()
        
        # Métricas de LLM
        llm_metrics = llm_service.get_metrics()
        
        # Métricas de banco de dados (simplificado)
        db_metrics = {
            "status": "healthy" if is_database_healthy() else "unhealthy",
            # Em uma implementação real, poderíamos adicionar mais métricas
            # como número de conexões, tempo de resposta, etc.
        }
        
        return MetricsResponse(
            system=system_metrics,
            database=db_metrics,
            embedding=embedding_metrics,
            llm=llm_metrics
        )
        
    except Exception as e:
        logger.error(f"Erro ao coletar métricas: {e}")
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