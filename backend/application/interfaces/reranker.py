from abc import ABC, abstractmethod
from typing import List, Tuple
from domain.aggregates.document.chunk import Chunk # Importar entidade Chunk

class ReRanker(ABC):
    """
    Interface abstrata para serviços de re-ranking.

    Define o contrato para reordenar uma lista de chunks recuperados
    com base na sua relevância para uma consulta específica, retornando os scores.
    """

    @abstractmethod
    async def rerank(
        self,
        query: str,
        chunks: List[Chunk]
    ) -> List[Tuple[Chunk, float]]:
        """
        Reordena uma lista de chunks com base na relevância para a consulta, retornando os scores.

        Args:
            query: A consulta original do usuário.
            chunks: A lista de chunks recuperados pela busca inicial (vetorial ou híbrida).

        Returns:
            Uma nova lista de tuplas (Chunk, float), onde float é o score de relevância,
            ordenada pela relevância (score mais alto primeiro).
        """
        pass
