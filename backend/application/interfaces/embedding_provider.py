from abc import ABC, abstractmethod
from typing import List
from domain.value_objects.embedding import Embedding

class EmbeddingProvider(ABC):
    """
    Interface para serviços de geração de embeddings vetoriais.

    Define o contrato para gerar embeddings tanto para textos individuais
    quanto para lotes de textos.
    """

    @abstractmethod
    async def embed_text(self, text: str) -> Embedding:
        """
        Gera o embedding vetorial para um único texto.

        Args:
            text: A string de texto a ser convertida em embedding.

        Returns:
            O embedding gerado como um objeto Embedding.

        Raises:
            Exception: Em caso de erro durante a geração do embedding.
        """
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[Embedding]:
        """
        Gera embeddings vetoriais para uma lista de textos em lote.

        Args:
            texts: Uma lista de strings de texto.

        Returns:
            Uma lista de objetos Embedding.
            A ordem dos embeddings corresponde à ordem dos textos de entrada.

        Raises:
            Exception: Em caso de erro durante a geração dos embeddings.
        """
        pass
