from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any

class TextExtractor(ABC):
    """ Interface para serviços de extração de texto de documentos. """

    @abstractmethod
    async def extract(self, file_content: bytes, file_type: str) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
        """
        Extrai texto e metadados opcionais de um conteúdo de arquivo binário.

        Args:
            file_content: Conteúdo binário do arquivo.
            file_type: O tipo/extensão do arquivo (ex: 'pdf', 'txt').

        Returns:
            Uma tupla contendo:
            - str: O texto extraído.
            - Dict[str, Any]: Metadados extraídos do documento (ex: autor, título de PDF).
            - Dict[str, Any]: Informações sobre a estrutura do documento (ex: TOC, seções).
        """
        pass
