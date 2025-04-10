from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional # Adicionar Dict, Any, Optional

# Opcional, mas recomendado: Importar Document do Langchain se for usar como tipo
# from langchain_core.documents import Document

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

    @abstractmethod
    async def split_page_to_chunks(
        self,
        page_number: int,
        page_text: str,
        base_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]: # Retorna lista de dicts com 'text' e 'metadata' (incluindo page_number)
         """
         Divide o texto de uma única página em chunks, preservando/adicionando metadados.

         Args:
             page_number: O número da página (1-indexado).
             page_text: O texto completo da página.
             base_metadata: Metadados adicionais a serem incluídos em cada chunk.

         Returns:
             Uma lista de dicionários, onde cada dicionário representa um chunk
             e contém 'text' (str) e 'metadata' (Dict). O metadata DEVE
             incluir a chave 'page_number'.
         """
         pass

    @abstractmethod
    async def evaluate_chunk(self, chunk_text: str) -> Optional[float]:
         """ Avalia a qualidade de um único chunk (opcional). """
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
