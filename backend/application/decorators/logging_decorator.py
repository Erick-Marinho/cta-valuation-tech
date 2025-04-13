import functools
import logging
import time
from typing import Any, Callable

# Configure o logger (pode ser configurado de forma mais centralizada posteriormente)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def log_execution(func: Callable) -> Callable:
    """
    Decorator para registrar o início, fim, argumentos, resultado e exceções
    da execução de uma função.
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        func_name = func.__name__
        # Tenta obter 'self' ou 'cls' para identificar a classe (se for um método)
        instance_or_class = args[0] if args and hasattr(args[0], func_name) else None
        class_name = instance_or_class.__class__.__name__ if instance_or_class else None
        log_prefix = f"{class_name}.{func_name}" if class_name else func_name

        logger.info(f"Iniciando execução: {log_prefix}")
        # Log dos argumentos (cuidado com dados sensíveis em produção)
        # logger.debug(f"Argumentos: args={args}, kwargs={kwargs}") # Nível DEBUG pode ser mais apropriado

        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            duration = end_time - start_time
            logger.info(f"Execução concluída: {log_prefix} em {duration:.4f} segundos.")
            # logger.debug(f"Resultado: {result}") # Nível DEBUG pode ser mais apropriado
            return result
        except Exception as e:
            end_time = time.perf_counter()
            duration = end_time - start_time
            logger.error(f"Erro durante execução de {log_prefix} após {duration:.4f} segundos: {e}", exc_info=True)
            raise # Re-levanta a exceção para não alterar o comportamento

    return wrapper

# Exemplo de uso (pode ser removido depois):
# @log_execution
# def example_function(a, b=2):
#     time.sleep(0.1)
#     if a > 5:
#         raise ValueError("Valor muito alto!")
#     return a + b

# if __name__ == '__main__':
#     print(f"Resultado 1: {example_function(3)}")
#     try:
#         example_function(10)
#     except ValueError as e:
#         print(f"Capturada exceção esperada: {e}")
