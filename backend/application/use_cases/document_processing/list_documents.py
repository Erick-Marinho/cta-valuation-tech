from typing import List, Optional, Tuple
from domain.aggregates.document.document import Document
from domain.repositories.document_repository import DocumentRepository
import asyncio
# Idealmente, usaríamos DTOs aqui, mas vamos começar simples
# from ...dtos.document_dto import DocumentDTO

class ListDocumentsUseCase:
    """
    Caso de Uso para listar documentos existentes, incluindo contagem total.
    """
    def __init__(self, document_repository: DocumentRepository):
        # Garante que o repositório foi injetado
        if document_repository is None:
            raise ValueError("DocumentRepository cannot be None")
        self._document_repository = document_repository

    async def execute(self, limit: int = 100, offset: int = 0) -> Tuple[List[Document], int]:
        """
        Executa o caso de uso, buscando uma página de documentos e a contagem total.

        Args:
            limit: Número máximo de documentos a retornar na página.
            offset: Número de documentos a pular (para paginação).

        Returns:
            Uma tupla contendo:
            - List[Document]: A lista de documentos da página solicitada.
            - int: O número total de documentos existentes.
        """
        # Executar ambas as queries (busca paginada e contagem total) concorrentemente
        # Usar asyncio.gather para eficiência
        try:
            results = await asyncio.gather(
                self._document_repository.find_all(limit=limit, offset=offset),
                self._document_repository.count_all()
            )
            documents_page = results[0]
            total_documents = results[1]
            return documents_page, total_documents
        except Exception as e:
             # Logar o erro aqui é uma boa prática
             # logger.exception(f"Erro no ListDocumentsUseCase ao buscar dados: {e}")
             # Relançar para ser tratado pela camada de interface
             # Poderia envolver em uma exceção específica da aplicação
             print(f"ERROR in ListDocumentsUseCase: {e}") # Log temporário
             raise # Relança a exceção original

        # TODO: Adicionar Tracing/Logging/Metrics aqui usando Decorators ou Middlewares
        # TODO: Converter para DTOs antes de retornar
