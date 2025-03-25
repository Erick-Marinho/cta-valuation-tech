"""
Utilitários para coleta de métricas e monitoramento de desempenho.
"""
import time
import logging
import functools
from datetime import datetime
from typing import Dict, Any, Callable, TypeVar, cast

logger = logging.getLogger(__name__)

# Métricas coletadas em memória (em uma aplicação real, seria enviado para um sistema como Prometheus)
_metrics = {
    "embedding_usage_count": 0,
    "embedding_text_chars_total": 0,
    "api_requests_total": 0,
    "function_timing": {},
    "errors_total": 0
}

T = TypeVar('T')

def track_timing(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator para medir o tempo de execução de uma função.
    
    Args:
        func: Função a ser monitorada
        
    Returns:
        Callable: Função decorada que reporta timing
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Registrar métrica
            func_name = func.__name__
            if func_name not in _metrics["function_timing"]:
                _metrics["function_timing"][func_name] = {"count": 0, "total_time": 0.0, "avg_time": 0.0}
            
            _metrics["function_timing"][func_name]["count"] += 1
            _metrics["function_timing"][func_name]["total_time"] += execution_time
            _metrics["function_timing"][func_name]["avg_time"] = (
                _metrics["function_timing"][func_name]["total_time"] / 
                _metrics["function_timing"][func_name]["count"]
            )
            
            # Log para funções que demoram muito
            if execution_time > 1.0:  # segundos
                logger.info(f"Função {func.__name__} executou em {execution_time:.4f}s")
                
            return result
            
        except Exception as e:
            _metrics["errors_total"] += 1
            execution_time = time.time() - start_time
            logger.error(f"Erro em {func.__name__}: {str(e)} (após {execution_time:.4f}s)")
            raise
            
    return cast(Callable[..., T], wrapper)

def track_embedding_usage(text_length: int):
    """
    Registra uso de embeddings para monitoramento de custos e desempenho.
    
    Args:
        text_length: Comprimento do texto enviado para embedding
    """
    _metrics["embedding_usage_count"] += 1
    _metrics["embedding_text_chars_total"] += text_length

def track_api_request(endpoint: str):
    """
    Registra uma requisição à API.
    
    Args:
        endpoint: Endpoint solicitado
    """
    _metrics["api_requests_total"] += 1
    
    # Em uma implementação real, seria por endpoint
    if "api_requests_by_endpoint" not in _metrics:
        _metrics["api_requests_by_endpoint"] = {}
        
    if endpoint not in _metrics["api_requests_by_endpoint"]:
        _metrics["api_requests_by_endpoint"][endpoint] = 0
        
    _metrics["api_requests_by_endpoint"][endpoint] += 1

def get_performance_metrics() -> Dict[str, Any]:
    """
    Retorna as métricas coletadas.
    
    Returns:
        dict: Métricas de desempenho da aplicação
    """
    return {
        **_metrics,
        "timestamp": datetime.now().isoformat()
    }