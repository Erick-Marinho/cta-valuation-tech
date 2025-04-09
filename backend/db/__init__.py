"""
Módulo de Banco de Dados - Contém principalmente modelos legados.

A lógica de conexão, schema e repositórios foi movida para a camada
de Infraestrutura e não deve ser acessada através deste módulo.
"""

import logging # Logging pode ser mantido se desejado, ou removido

# Configuração de logging (pode ser movida para um local centralizado)
# logging.basicConfig(
#     level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# )

# --- Imports REMOVIDOS ---
# from .connection import (
#     get_connection,
#     get_cursor,
#     close_connection,
#     execute_query,
#     execute_query_single_result,
#     execute_transaction,
# )
# from .schema import setup_database, check_database_version, is_database_healthy
# from .repositories.document_repository import DocumentoRepository
# from .repositories.chunk_repository import ChunkRepository
# --- Fim dos Imports REMOVIDOS ---


# Importação de modelos (Manter se a pasta db/models ainda existe)
# Se você mover os modelos para ORM na infraestrutura, remova isso também.
try:
    from .models.document import Documento
    from .models.chunk import Chunk
    MODELS_PRESENT = True
except ImportError:
    # Caso a pasta models também seja removida/movida no futuro
    Documento = None
    Chunk = None
    MODELS_PRESENT = False
    logging.warning("Modelos legados não encontrados em db/models.")


# Exportar apenas o que ainda existe e é relevante (provavelmente só os modelos legados)
__all__ = []
if MODELS_PRESENT:
    __all__.extend(["Documento", "Chunk"])


# --- Função de Inicialização REMOVIDA ---
# def initialize_db():
#    ... (código removido) ...
# --- Fim da Função REMOVIDA ---


# --- Lógica de Auto-Inicialização REMOVIDA ---
# import os
# if os.getenv("AUTO_INIT_DB", "false").lower() == "true":
#     initialize_db()
# --- Fim da Auto-Inicialização REMOVIDA ---
