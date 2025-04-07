"""
Repositórios para acesso aos dados das entidades no banco de dados.
"""

from .document_repository import DocumentoRepository
from .chunk_repository import ChunkRepository

__all__ = ["DocumentoRepository", "ChunkRepository"]
