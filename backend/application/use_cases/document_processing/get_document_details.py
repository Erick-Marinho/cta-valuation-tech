import logging
from typing import Optional

# Importar entidade e repositório do domínio
from domain.aggregates.document.document import Document
from domain.repositories.document_repository import DocumentRepository

# Importar exceção personalizada (opcional, mas bom)
# from application.exceptions import DocumentNotFound

logger = logging.getLogger(__name__)

class GetDocumentDetailsUseCase:
    """
    Caso de Uso para obter os detalhes de um documento específico por ID.
    """

    def __init__(self, document_repository: DocumentRepository):
        self._doc_repo = document_repository
        if self._doc_repo is None:
             raise ValueError("DocumentRepository cannot be None")

    async def execute(self, document_id: int) -> Optional[Document]:
        """
        Busca um documento pelo seu ID.

        Args:
            document_id: O ID do documento a ser buscado.

        Returns:
            A entidade Document encontrada, ou None se não existir.
            (Nota: No futuro, retornar um DTO específico pode ser melhor
             para desacoplar a resposta da entidade interna).
        """
        logger.info(f"Buscando detalhes para o documento ID: {document_id}")
        try:
            document = await self._doc_repo.find_by_id(document_id)
            if document is None:
                 logger.warning(f"Documento com ID {document_id} não encontrado.")
                 # Opcionalmente, poderia lançar DocumentNotFound aqui
                 # raise DocumentNotFound(f"Documento com ID {document_id} não encontrado.")
                 return None
            else:
                 logger.info(f"Documento {document_id} encontrado: {document.name}")
                 # O repositório já deve retornar o Document completo (com metadados, etc.)
                 # Se precisasse buscar chunks associados, faria isso aqui ou em outro UseCase.
                 return document
        except Exception as e:
            logger.exception(f"Erro ao buscar documento ID {document_id} no repositório: {e}")
            # Relançar como uma exceção genérica ou específica da aplicação
            raise RuntimeError(f"Erro ao buscar detalhes do documento: {e}") from e
