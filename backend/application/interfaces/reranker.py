from abc import ABC, abstractmethod
from typing import List
from domain.aggregates.document.chunk import Chunk # Importar entidade Chunk

class ReRanker(ABC):
    """
    Interface abstrata para serviços de re-ranking.

    Define o contrato para reordenar uma lista de chunks recuperados
    com base na sua relevância para uma consulta específica.
    """

    @abstractmethod
    async def rerank(
        self,
        query: str,
        chunks: List[Chunk]
    ) -> List[Chunk]:
        """
        Reordena uma lista de chunks com base na relevância para a consulta.

        Args:
            query: A consulta original do usuário.
            chunks: A lista de chunks recuperados pela busca inicial (vetorial ou híbrida).

        Returns:
            Uma nova lista de Chunks, reordenada pela relevância (mais relevante primeiro).
            A lista pode ou não conter todos os chunks originais, dependendo da implementação.
        """
        pass
