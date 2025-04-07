"""
Inicialização do módulo de banco de dados.
Fornece acesso direto aos principais componentes.
"""

import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Importações para facilitar o acesso
from .connection import (
    get_connection,
    get_cursor,
    close_connection,
    execute_query,
    execute_query_single_result,
    execute_transaction,
)

from .schema import setup_database, check_database_version, is_database_healthy

# Importação de modelos
from .models.document import Documento
from .models.chunk import Chunk

# Importação de repositórios
from .repositories.document_repository import DocumentoRepository
from .repositories.chunk_repository import ChunkRepository

# Exportar para facilitar imports
__all__ = [
    # Connection
    "get_connection",
    "get_cursor",
    "close_connection",
    "execute_query",
    "execute_query_single_result",
    "execute_transaction",
    # Schema
    "setup_database",
    "check_database_version",
    "is_database_healthy",
    # Models
    "Documento",
    "Chunk",
    # Repositories
    "DocumentoRepository",
    "ChunkRepository",
]


# Inicialização automática ao importar o módulo
def initialize_db():
    """
    Configura o banco de dados ao inicializar o módulo.
    """
    try:
        setup_database()
        version = check_database_version()
        logging.info(f"Banco de dados inicializado - versão {version}")
    except Exception as e:
        logging.error(f"Erro ao inicializar banco de dados: {e}")


# Inicialização automática se solicitada via variável de ambiente
import os

if os.getenv("AUTO_INIT_DB", "false").lower() == "true":
    initialize_db()
