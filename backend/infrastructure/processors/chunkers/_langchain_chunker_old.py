import asyncio
import logging
from typing import List, Dict, Any, Optional

# Importar Interface da Aplicação
from application.interfaces.chunker import Chunker # Apenas Chunker é necessário aqui

# Imports Langchain
from langchain_text_splitters import RecursiveCharacterTextSplitter, TextSplitter
from langchain_core.documents import Document

# Imports da Aplicação
from config.config import get_settings

logger = logging.getLogger(__name__)

class LangchainChunker(Chunker):
    """
    Implementação de Chunker focada na divisão de páginas usando
    RecursiveCharacterTextSplitter do Langchain.
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ):
        """Inicializa o chunker com configurações específicas ou dos settings."""
        self.settings = get_settings()
        _chunk_size = chunk_size or self.settings.CHUNK_SIZE
        _chunk_overlap = chunk_overlap or self.settings.CHUNK_OVERLAP

        # Inicializar o splitter (ex: RecursiveCharacterTextSplitter)
        self.splitter: TextSplitter = RecursiveCharacterTextSplitter(
            chunk_size=_chunk_size,
            chunk_overlap=_chunk_overlap,
            length_function=len,
            is_separator_regex=False,
            separators=["\n\n", "\n", ". ", ", ", " ", ""], # Ordem importa
        )
        logger.info(f"LangchainChunker (RecursiveCharacterTextSplitter) inicializado com chunk_size={_chunk_size}, chunk_overlap={_chunk_overlap}")

    # --- Implementação do ÚNICO método da interface Chunker ---
    async def split_page_to_chunks(
        self,
        page_number: int,
        page_text: str,
        base_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """ Divide texto da página, adicionando metadados a cada chunk. """
        if not page_text:
            return []

        page_metadata = base_metadata or {}
        page_metadata["page_number"] = page_number

        try:
            # Função síncrona para o splitter
            def sync_split():
                return self.splitter.create_documents([page_text], metadatas=[page_metadata])

            # Executar em thread separada
            split_docs: List[Document] = await asyncio.to_thread(sync_split)

            # Converter Documentos Langchain para o formato de dicionário esperado
            chunk_list = []
            for i, doc in enumerate(split_docs):
                chunk_metadata = doc.metadata or {}
                if "page_number" not in chunk_metadata:
                     logger.warning(f"Chunk {i} da página {page_number} perdeu metadado 'page_number'. Adicionando manualmente.")
                     chunk_metadata["page_number"] = page_number

                # Adicionar verificação para não incluir chunks vazios após split
                if doc.page_content and doc.page_content.strip():
                     chunk_list.append({
                         "text": doc.page_content,
                         "metadata": chunk_metadata
                     })
                else:
                     logger.debug(f"Chunk vazio descartado da página {page_number}, índice {i}.")


            logger.info(f"Página {page_number} dividida em {len(chunk_list)} chunks usando RecursiveCharacterTextSplitter.")
            return chunk_list

        except Exception as e:
            logger.error(f"Erro ao dividir texto da página {page_number} com RecursiveCharacterTextSplitter: {e}", exc_info=True)
            return [] # Retorna lista vazia em caso de erro

    # --- Métodos Removidos ---
    # REMOVIDO: chunk_text(...)
    # REMOVIDO: evaluate_chunk(...)
    # REMOVIDO: chunk(...) com seleção de estratégia
