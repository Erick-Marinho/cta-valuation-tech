import logging

# Importar interfaces de repositórios do domínio
from domain.repositories.document_repository import DocumentRepository
from domain.repositories.chunk_repository import ChunkRepository

# Importar exceção personalizada (opcional)
# from application.exceptions import DocumentNotFound

logger = logging.getLogger(__name__)

class DeleteDocumentUseCase:
    """
    Caso de Uso para excluir um documento e todos os seus chunks associados.
    """

    def __init__(
        self,
        document_repository: DocumentRepository,
        chunk_repository: ChunkRepository
    ):
        self._doc_repo = document_repository
        self._chunk_repo = chunk_repository
        if self._doc_repo is None or self._chunk_repo is None:
             raise ValueError("DocumentRepository and ChunkRepository cannot be None")

    async def execute(self, document_id: int) -> bool:
        """
        Exclui um documento e seus chunks pelo ID do documento.

        Args:
            document_id: O ID do documento a ser excluído.

        Returns:
            True se o documento (e seus chunks) foram excluídos ou se o
            documento já não existia. False se ocorreu um erro inesperado
            durante a exclusão.
            (Alternativa: Lançar DocumentNotFound se o documento não existe).
        """
        logger.info(f"Iniciando exclusão do documento ID: {document_id} e seus chunks.")

        try:
            # 1. Excluir Chunks associados (é seguro chamar mesmo se não houver chunks)
            # O método do repositório retorna a contagem, podemos logar se quisermos.
            deleted_chunks_count = await self._chunk_repo.delete_by_document_id(document_id)
            logger.info(f"{deleted_chunks_count} chunks excluídos para o documento ID: {document_id}.")

            # 2. Excluir o Documento principal
            # O método do repositório retorna True/False indicando se a exclusão ocorreu.
            deleted_document = await self._doc_repo.delete(document_id)

            if not deleted_document:
                # Se delete retornou False, pode significar que o documento
                # não foi encontrado para ser excluído. Consideramos isso sucesso?
                # Ou deveríamos verificar a existência primeiro com find_by_id?
                # Abordagem atual: Considera sucesso se não estava lá ou foi deletado.
                logger.warning(f"Documento principal com ID {document_id} não encontrado para exclusão (ou já excluído).")
                # Poderia lançar DocumentNotFound aqui se quiséssemos tratar diferente.
                # raise DocumentNotFound(f"Documento com ID {document_id} não encontrado para exclusão.")

            logger.info(f"Exclusão concluída para documento ID: {document_id}. Documento principal excluído: {deleted_document}")
            return True # Retorna True indicando que a operação foi concluída (ou não era necessária)

        except Exception as e:
            logger.exception(f"Erro ao excluir documento ID {document_id} e/ou seus chunks: {e}")
            # Retornar False ou relançar uma exceção específica
            # raise RuntimeError(f"Erro ao excluir documento: {e}") from e
            return False
