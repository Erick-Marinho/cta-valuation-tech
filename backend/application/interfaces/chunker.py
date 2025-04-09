from abc import ABC, abstractmethod
from typing import List, Dict, Any # Adicionar Dict, Any para quality

class Chunker(ABC):
    """ Interface para serviços de divisão de texto (chunking). """

    @abstractmethod
    async def chunk(self, text: str, strategy: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """
        Divide um texto longo em chunks menores usando uma estratégia específica.

        Args:
            text: O texto a ser dividido.
            strategy: A estratégia de chunking a ser usada (ex: 'semantic', 'simple', 'header_based').
            chunk_size: O tamanho alvo dos chunks.
            chunk_overlap: A sobreposição entre chunks consecutivos.

        Returns:
            Uma lista de strings, onde cada string é um chunk de texto.
        """
        pass

# Opcional: Interface separada para avaliação de qualidade
class ChunkQualityEvaluator(ABC):
    """ Interface para serviços de avaliação da qualidade dos chunks. """

    @abstractmethod
    async def evaluate(self, chunks: List[str], original_text: str) -> Dict[str, Any]:
        """
        Avalia a qualidade dos chunks gerados.

        Args:
            chunks: A lista de chunks gerados.
            original_text: O texto original completo.

        Returns:
            Um dicionário contendo métricas de qualidade (ex: {'avg_coherence': 0.85}).
        """
        pass
