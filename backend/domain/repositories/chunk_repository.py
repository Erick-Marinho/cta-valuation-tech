from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple # Adicionar Dict, Any para save_batch e Tuple
# Importar a entidade Chunk do domínio
from ..aggregates.document.chunk import Chunk

class ChunkRepository(ABC):
    """
    Interface para o repositório de Chunks. Define o contrato
    para operações de persistência relacionadas à entidade Chunk.
    """

    @abstractmethod
    async def save(self, chunk: Chunk) -> Chunk:
        """ Salva (cria ou atualiza) um único chunk. """
        # Pode ser menos usado se preferirmos sempre salvar em lote.
        pass

    @abstractmethod
    async def save_batch(self, chunks: List[Chunk]) -> List[Chunk]:
        """
        Salva uma lista de chunks de forma eficiente (em lote).
        Retorna os chunks salvos (potencialmente com IDs preenchidos).
        """
        # Nota: A implementação original `criar_chunks_em_lote` recebia
        # uma lista de dicionários. Aqui recebemos entidades Chunk.
        # A implementação concreta cuidará do mapeamento para o formato do DB.
        pass

    @abstractmethod
    async def find_by_id(self, chunk_id: int) -> Optional[Chunk]:
        """ Busca um chunk pelo seu ID. """
        pass

    @abstractmethod
    async def find_by_document_id(self, document_id: int) -> List[Chunk]:
        """ Busca todos os chunks pertencentes a um documento específico. """
        pass

    @abstractmethod
    async def delete_by_document_id(self, document_id: int) -> int:
        """ Exclui todos os chunks associados a um documento. Retorna o número de chunks excluídos. """
        pass

    # Interface para busca vetorial pode ser adicionada aqui ou em um serviço separado
    @abstractmethod
    async def find_similar_chunks(
        self,
        embedding_vector: List[float],
        limit: int,
        filter_document_ids: Optional[List[int]] = None
    ) -> List[Tuple[Chunk, float]]: # <-- MUDANÇA: Retorna tupla com score
         """ Encontra chunks semanticamente similares a um dado vetor de embedding, retornando scores. """
         pass

    @abstractmethod
    async def find_by_keyword(self, query: str, limit: int, filter_document_ids: Optional[List[int]] = None) -> List[Tuple[Chunk, float]]:
        """ Encontra chunks baseados na relevância textual (keyword search), retornando scores. """
        pass

    # Métodos adicionais podem ser necessários, como busca por similaridade vetorial.
    # No entanto, a busca vetorial muitas vezes retorna mais do que apenas a entidade Chunk
    # (ex: scores), então pode ser melhor definida em um serviço de busca ou caso de uso específico
    # que usa o repositório internamente. Vamos manter o repositório focado no CRUD por enquanto.
    # @abstractmethod
    # async def find_similar(self, embedding: List[float], limit: int = 5, ...) -> List[SearchResult]:
    #     pass
