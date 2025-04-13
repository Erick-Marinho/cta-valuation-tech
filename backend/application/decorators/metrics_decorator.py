import functools
import time
import logging
from typing import Any, Callable

# Importar as métricas específicas do arquivo (localização ATUALIZADA e CORRIGIDA)
# from infrastructure.metrics.prometheus import USE_CASE_CALLS_TOTAL, USE_CASE_LATENCY_SECONDS # <-- Linha antiga comentada/removida
from infrastructure.metrics.prometheus.metrics_prometheus import USE_CASE_CALLS_TOTAL, USE_CASE_LATENCY_SECONDS # <-- Linha corrigida

logger = logging.getLogger(__name__)

def track_use_case_metrics(func: Callable) -> Callable:
    """
    Decorator para registrar métricas Prometheus (chamadas, latência, status)
    para a execução de um caso de uso.
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # O primeiro argumento de um método de instância é 'self'
        instance = args[0] if args else None
        use_case_name = instance.__class__.__name__ if instance else func.__name__
        status = "success" # Assume sucesso inicialmente
        start_time = time.perf_counter()

        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            status = "error" # Muda status em caso de erro
            logger.error(f"Erro no caso de uso {use_case_name}: {e}", exc_info=False) # Log breve, o log_decorator pode logar detalhes
            raise # Re-levanta a exceção
        finally:
            duration = time.perf_counter() - start_time
            # Registrar métricas
            USE_CASE_LATENCY_SECONDS.labels(use_case=use_case_name).observe(duration)
            USE_CASE_CALLS_TOTAL.labels(use_case=use_case_name, status=status).inc()
            logger.debug(f"Métricas registradas para {use_case_name}: status={status}, duration={duration:.4f}s")

    return wrapper

# Exemplo de uso (pode ser removido depois):
# from utils.metrics_prometheus import * # Importar tudo para o exemplo
# class DummyUseCase:
#     @track_use_case_metrics
#     def execute(self, succeed=True):
#         time.sleep(0.05)
#         if not succeed:
#             raise ValueError("Falha simulada")
#         return "OK"

# if __name__ == '__main__':
#     # Nota: Para ver as métricas, seria necessário um endpoint /metrics
#     use_case = DummyUseCase()
#     print(use_case.execute(succeed=True))
#     try:
#         use_case.execute(succeed=False)
#     except ValueError:
#         print("Capturada falha simulada.")
#     # Em um servidor real, as métricas poderiam ser verificadas via /metrics
