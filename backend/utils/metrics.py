"""
Utilitário mínimo para tracking de timing de funções.
"""
import time
import logging
import functools
from typing import Callable, TypeVar, cast

logger = logging.getLogger(__name__)

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
            
            # Log para funções que demoram muito
            if execution_time > 1.0:  # segundos
                logger.info(f"Função {func.__name__} executou em {execution_time:.4f}s")
                
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Erro em {func.__name__}: {str(e)} (após {execution_time:.4f}s)")
            raise
            
    return cast(Callable[..., T], wrapper)

