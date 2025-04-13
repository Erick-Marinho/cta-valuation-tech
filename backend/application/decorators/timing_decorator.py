import functools
import logging
import time
from typing import Any, Callable

# Use o mesmo logger ou um logger específico para timing
logger = logging.getLogger(__name__) # Ou logging.getLogger('timing')

def log_execution_time(func: Callable) -> Callable:
    """
    Decorator para registrar o tempo de execução de uma função.
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        func_name = func.__name__
        # Tenta obter 'self' ou 'cls' para identificar a classe (se for um método)
        instance_or_class = args[0] if args and hasattr(args[0], func_name) else None
        class_name = instance_or_class.__class__.__name__ if instance_or_class else None
        log_prefix = f"{class_name}.{func_name}" if class_name else func_name

        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result # Retorna o resultado imediatamente após a execução
        finally:
            # O bloco finally garante que o tempo seja registrado mesmo se ocorrer uma exceção
            end_time = time.perf_counter()
            duration = end_time - start_time
            logger.info(f"Tempo de execução para {log_prefix}: {duration:.4f} segundos.")
            # Nota: Não capturamos ou logamos a exceção aqui, apenas o tempo.
            # O decorator log_execution já lida com o log de erros.

    return wrapper

# Exemplo de uso (pode ser removido depois):
# @log_execution_time
# def example_timed_function(delay):
#     time.sleep(delay)
#     return f"Dormi por {delay} segundos."

# if __name__ == '__main__':
#     print(example_timed_function(0.2))
