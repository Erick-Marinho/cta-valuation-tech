import logging
import functools
import time
from typing import Callable, TypeVar, Any, cast

# O TypeVar T não é mais usado após remover track_timing, pode ser removido também
# T = TypeVar("T")


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
        handlers=[logging.StreamHandler()], # Logs para o console por padrão
    )

    # Configurar handlers adicionais (arquivo)
    if log_file:
        import os
        # Garante que o diretório do arquivo de log exista
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
             try:
                 os.makedirs(log_dir, exist_ok=True)
                 logging.info(f"Diretório de log criado: {log_dir}")
             except OSError as e:
                 logging.error(f"Não foi possível criar o diretório de log {log_dir}: {e}")
                 # Decide não adicionar o handler de arquivo se o diretório falhar
                 log_file = None # Impede a adição do handler abaixo

        if log_file: # Verifica novamente se log_file ainda é válido
            file_handler = logging.FileHandler(log_file, encoding='utf-8') # Adiciona encoding
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            )
            logging.getLogger().addHandler(file_handler)
            logging.info(f"Logging configurado também para o arquivo: {log_file}")


    # Definir níveis para bibliotecas de terceiros muito verbosas (ajuste conforme necessário)
    logging.getLogger("httpx").setLevel(logging.WARNING) # Exemplo comum com FastAPI/HTTPX
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING) # Uvicorn access logs podem ser verbosos
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    # logging.getLogger("urllib3").setLevel(logging.WARNING)
    # logging.getLogger("elasticsearch").setLevel(logging.WARNING)

    # Registrar início da configuração
    logging.info(f"Logging configurado com nível {log_level}")


def get_logger(name: str) -> logging.Logger: # Adicionado type hint para o retorno
    """
    Obtém um logger configurado para o módulo especificado.

    Args:
        name: Nome do módulo ou componente (geralmente __name__)

    Returns:
        logging.Logger: Logger configurado
    """
    return logging.getLogger(name)


# O decorator track_timing foi removido daqui
