from abc import ABC, abstractmethod
from typing import List

class EmbeddingProvider(ABC):
    """ Interface para serviços de geração de embeddings. """

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Gera embeddings vetoriais para uma lista de textos.

        Args:
            texts: Uma lista de strings de texto.

        Returns:
            Uma lista de embeddings, onde cada embedding é uma lista de floats.
            A ordem dos embeddings corresponde à ordem dos textos de entrada.
        """
        pass
