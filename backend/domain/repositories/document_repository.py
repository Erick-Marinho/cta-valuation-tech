from abc import ABC, abstractmethod
from typing import Optional, List
from ..aggregates.document.document import Document # Importa a entidade de domínio

class DocumentRepository(ABC):
    """
    Interface para o repositório de documentos. Define o contrato
    para operações de persistência relacionadas à entidade Document.
    """

    @abstractmethod
    async def save(self, document: Document) -> Document:
        """Salva (cria ou atualiza) um documento."""
        pass

    @abstractmethod
    async def find_by_id(self, document_id: int) -> Optional[Document]:
        """Busca um documento pelo seu ID."""
        pass

    @abstractmethod
    async def find_all(self, limit: int = 100, offset: int = 0) -> List[Document]:
        """Lista todos os documentos com paginação."""
        pass

    @abstractmethod
    async def delete(self, document_id: int) -> bool:
        """Exclui um documento pelo seu ID."""
        pass

    # Adicionar outros métodos conforme necessário (ex: find_by_name, count, etc.)
