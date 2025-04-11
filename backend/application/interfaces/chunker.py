from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

# Opcional, mas recomendado: Importar Document do Langchain se for usar como tipo
# from langchain_core.documents import Document

class Chunker(ABC):
    """
    Interface para serviços de divisão de texto (chunking) focado em páginas.

    Define o contrato para dividir o texto de uma página em múltiplos chunks,
    preservando e adicionando metadados relevantes.
    """

    @abstractmethod
    async def split_page_to_chunks(
        self,
        page_number: int,
        page_text: str,
        base_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]: # Retorna lista de dicts com 'text' e 'metadata'
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
