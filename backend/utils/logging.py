import logging
import functools
import time
from typing import Callable, TypeVar, Any, cast

T = TypeVar("T")


def configure_logging(log_level=None, log_file=None):
    """
    Configura o logging para toda a aplicação.

    Args:
        log_level: Nível de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Caminho para arquivo de log (opcional)
    """
    # Determinar nível de log
    if log_level is None:
        import os

        log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # Converter string para constante de logging
    numeric_level = getattr(logging, log_level, logging.INFO)

    # Configuração básica
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )

    # Configurar handlers
    if log_file:
        import os

        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logging.getLogger().addHandler(file_handler)

    # Definir níveis para bibliotecas de terceiros muito verbosas
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("elasticsearch").setLevel(logging.WARNING)

    # Registrar início da configuração
    logging.info(f"Logging configurado com nível {log_level}")


def get_logger(name):
    """
    Obtém um logger configurado para o módulo especificado.

    Args:
        name: Nome do módulo ou componente

    Returns:
        logging.Logger: Logger configurado
    """
    return logging.getLogger(name)


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
        logger = logging.getLogger(func.__module__)
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
            logger.error(
                f"Erro em {func.__name__}: {str(e)} (após {execution_time:.4f}s)"
            )
            raise

    return cast(Callable[..., T], wrapper)
