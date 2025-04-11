import logging
from typing import Optional

# Importar entidade e repositório do domínio
from domain.aggregates.document.document import Document
from domain.repositories.document_repository import DocumentRepository

# Importar o DTO
from application.dtos.document_dto import DocumentDTO

# Importar exceção personalizada (opcional, mas bom)
# from application.exceptions import DocumentNotFound

logger = logging.getLogger(__name__)

class GetDocumentDetailsUseCase:
    """
    Caso de Uso para obter os detalhes de um documento específico por ID.
    Retorna um DTO para desacoplar da camada de domínio.
    """

    def __init__(self, document_repository: DocumentRepository):
        self._doc_repo = document_repository
        if self._doc_repo is None:
             logger.error("GetDocumentDetailsUseCase inicializado sem DocumentRepository.")
             raise ValueError("DocumentRepository cannot be None")

    async def execute(self, document_id: int) -> Optional[DocumentDTO]:
        """
        Busca um documento pelo seu ID e retorna seus detalhes como um DTO.

        Args:
            document_id: O ID do documento a ser buscado.

        Returns:
            Um DocumentDTO com os detalhes do documento encontrado,
            ou None se não existir.
        """
        logger.info(f"Executando GetDocumentDetailsUseCase para ID: {document_id}")
        try:
            # Busca a entidade de domínio
            document: Optional[Document] = await self._doc_repo.find_by_id(document_id)

            if document is None:
                 logger.warning(f"Documento com ID {document_id} não encontrado no repositório.")
                 # Opcionalmente, poderia lançar DocumentNotFound aqui
                 return None
            else:
                 logger.info(f"Documento {document_id} encontrado: {document.name}. Mapeando para DTO.")
                 # --- MAPEAMENTO DOMÍNIO -> DTO ---
                 document_dto = DocumentDTO(
                     id=document.id,
                     name=document.name,
                     file_type=document.file_type,
                     upload_date=document.upload_date,
                     size_kb=document.size_kb,
                     chunks_count=document.chunks_count,
                     processed=document.processed,
                     metadata=document.metadata.to_dict() if document.metadata else {},
                 )
                 # -------------------------------
                 return document_dto # Retorna o DTO

        except Exception as e:
            logger.exception(f"Erro ao buscar ou mapear documento ID {document_id}: {e}")
            # Relançar como uma exceção genérica ou específica da aplicação
            raise RuntimeError(f"Erro ao buscar detalhes do documento: {e}") from e
