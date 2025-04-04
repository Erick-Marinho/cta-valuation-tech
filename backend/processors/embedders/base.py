from abc import ABC, abstractmethod
from typing import List

from backend.core.models.chunk import Chunk


class Embedder(ABC):
    """Interface abstrata para geradores de embeddings."""

    @abstractmethod
    def embed(self, chunks: List[Chunk]) -> List[Chunk]:
        """
        Gera embeddings para uma lista de Chunks e atualiza os objetos Chunk.

        Args:
            chunks: Uma lista de instâncias de Chunk sem embeddings.

        Returns:
            A mesma lista de instâncias de Chunk com o atributo 'embedding' populado.
        """
        pass

    @abstractmethod
    async def aembed(self, chunks: List[Chunk]) -> List[Chunk]:
        """
        Versão assíncrona de 'embed'. Gera embeddings para uma lista de Chunks.

        Args:
            chunks: Uma lista de instâncias de Chunk sem embeddings.

        Returns:
            A mesma lista de instâncias de Chunk com o atributo 'embedding' populado.
        """
        pass