# backend/application/interfaces/text_extractor.py
from abc import ABC, abstractmethod
from typing import IO, List, Dict, Any, Tuple # Adicionar Tuple

class TextExtractor(ABC):
    """ Interface para serviços de extração de texto de documentos. """

    @abstractmethod
    async def extract_text(self, file_content: bytes, file_type: str) -> List[Dict[str, Any]]:
        """
        Extrai texto de um conteúdo de arquivo binário.

        Args:
            file_content: O conteúdo binário do arquivo.
            file_type: O tipo do arquivo (ex: 'pdf', 'docx').

        Returns:
            Uma lista de dicionários, onde cada dicionário representa uma página
            e contém pelo menos as chaves 'page_number' (int, 1-indexado) e 'text' (str).
            Ex: [{'page_number': 1, 'text': '...'}, {'page_number': 2, 'text': '...'}]

        Raises:
            NotImplementedError: Se o tipo de arquivo não for suportado.
            Exception: Para outros erros de processamento.
        """
        pass

    # --- NOVO MÉTODO ---
    @abstractmethod
    async def extract_document_metadata(self, file_content: bytes, file_type: str) -> Dict[str, Any]:
        """
        Extrai metadados gerais do documento (ex: título, autor).

        Args:
            file_content: O conteúdo binário do arquivo.
            file_type: O tipo do arquivo (ex: 'pdf', 'docx').

        Returns:
            Um dicionário contendo os metadados extraídos do documento.
            Retorna dicionário vazio se nenhum metadado for encontrado ou erro.

        Raises:
            NotImplementedError: Se o tipo de arquivo não for suportado.
            Exception: Para outros erros de processamento.
        """
        pass
    # --------------------
