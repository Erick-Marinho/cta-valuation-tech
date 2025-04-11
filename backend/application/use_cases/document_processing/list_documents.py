from typing import List, Optional, Tuple
from domain.aggregates.document.document import Document
from domain.repositories.document_repository import DocumentRepository
import asyncio
import logging
from application.dtos.document_dto import DocumentDTO

logger = logging.getLogger(__name__)

class ListDocumentsUseCase:
    """
    Caso de Uso para listar documentos existentes, incluindo contagem total.
    Retorna DTOs para desacoplar da camada de domínio.
    """
    def __init__(self, document_repository: DocumentRepository):
        if document_repository is None:
            logger.error("ListDocumentsUseCase inicializado sem DocumentRepository.")
            raise ValueError("DocumentRepository cannot be None")
        self._document_repository = document_repository

    async def execute(self, limit: int = 100, offset: int = 0) -> Tuple[List[DocumentDTO], int]:
        """
        Executa o caso de uso, buscando uma página de documentos e a contagem total.

        Args:
            limit: Número máximo de documentos a retornar na página.
            offset: Número de documentos a pular (para paginação).

        Returns:
            Uma tupla contendo:
            - List[DocumentDTO]: A lista de DTOs dos documentos da página solicitada.
            - int: O número total de documentos existentes.
        """
        logger.info(f"Executando ListDocumentsUseCase: limit={limit}, offset={offset}")
        try:
            results = await asyncio.gather(
                self._document_repository.find_all(limit=limit, offset=offset),
                self._document_repository.count_all()
            )
            documents_page: List[Document] = results[0]
            total_documents: int = results[1]

            logger.debug(f"Repositório retornou {len(documents_page)} documentos e contagem total {total_documents}.")

            document_dtos = [
                DocumentDTO(
                    id=doc.id,
                    name=doc.name,
                    file_type=doc.file_type,
                    upload_date=doc.upload_date,
                    size_kb=doc.size_kb,
                    chunks_count=doc.chunks_count,
                    processed=doc.processed,
                    metadata=doc.metadata,
                )
                for doc in documents_page if doc and doc.id is not None
            ]

            logger.info(f"Mapeados {len(document_dtos)} documentos para DTOs.")
            return document_dtos, total_documents

        except Exception as e:
             logger.exception(f"Erro no ListDocumentsUseCase ao buscar/mapear dados: {e}")
             raise RuntimeError(f"Erro ao listar documentos: {e}") from e

        # TODO: Adicionar Tracing/Metrics usando Decorators na camada de Aplicação
