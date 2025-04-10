import asyncio
import logging
from typing import List, Dict, Any, Optional

# Importar Interface da Aplicação
from application.interfaces.chunker import Chunker, ChunkQualityEvaluator

# Importar implementações concretas (dos novos locais na infraestrutura)
# Ajuste o caminho exato se necessário
from .semantic_chunker import create_semantic_chunks
# Importe o simple_chunker também se for mantê-lo
from .simple_chunker import create_simple_chunks

# Imports Langchain
from langchain_text_splitters import RecursiveCharacterTextSplitter, TextSplitter # Ou outro splitter
from langchain_core.documents import Document # Importar Document

# Imports da Aplicação
from config.config import get_settings # <-- CORREÇÃO: Importar de config.config

logger = logging.getLogger(__name__)

class LangchainChunker(Chunker):
    """
    Implementação de Chunker usando TextSplitters do Langchain.
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        # quality_evaluator: Optional[ChunkQualityEvaluator] = None # Remover se não usar mais
    ):
        self.settings = get_settings()
        # Usar valores dos settings como padrão
        _chunk_size = chunk_size or self.settings.CHUNK_SIZE
        _chunk_overlap = chunk_overlap or self.settings.CHUNK_OVERLAP
        # self.quality_evaluator = quality_evaluator # Remover se não usar mais

        # Inicializar o splitter (ex: RecursiveCharacterTextSplitter)
        # Ajustar separadores conforme necessidade
        self.splitter: TextSplitter = RecursiveCharacterTextSplitter(
            chunk_size=_chunk_size,
            chunk_overlap=_chunk_overlap,
            length_function=len,
            is_separator_regex=False,
            separators=["\n\n", "\n", ". ", ", ", " ", ""], # Ordem importa
        )
        logger.info(f"LangchainChunker inicializado com chunk_size={_chunk_size}, chunk_overlap={_chunk_overlap}")

    # Método antigo (pode manter com aviso ou remover)
    async def chunk_text(self, text: str) -> List[str]:
        logger.warning("Método chunk_text obsoleto chamado. Use split_page_to_chunks.")
        # A função split_text retorna apenas strings, perde metadados.
        return self.splitter.split_text(text)

    # Implementação do novo método
    async def split_page_to_chunks(
        self,
        page_number: int,
        page_text: str,
        base_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """ Divide texto da página, adicionando metadados a cada chunk. """
        if not page_text:
            return []

        # Criar metadados base para esta página
        page_metadata = base_metadata or {}
        page_metadata["page_number"] = page_number

        # Usar create_documents para que o splitter crie documentos com metadados
        # Ele tentará preservar os metadados fornecidos.
        try:
            # Função síncrona para o splitter
            def sync_split():
                # Passamos o texto da página e os metadados associados
                return self.splitter.create_documents([page_text], metadatas=[page_metadata])

            # Executar em thread separada
            split_docs: List[Document] = await asyncio.to_thread(sync_split)

            # Converter Documentos Langchain para o formato de dicionário esperado
            chunk_list = []
            for i, doc in enumerate(split_docs):
                # Verificar se o metadado page_number foi preservado (deve ter sido)
                chunk_metadata = doc.metadata or {}
                if "page_number" not in chunk_metadata:
                     logger.warning(f"Chunk {i} da página {page_number} perdeu metadado 'page_number'. Adicionando manualmente.")
                     chunk_metadata["page_number"] = page_number

                chunk_list.append({
                    "text": doc.page_content,
                    "metadata": chunk_metadata
                })
            logger.info(f"Página {page_number} dividida em {len(chunk_list)} chunks.")
            return chunk_list

        except Exception as e:
            logger.error(f"Erro ao dividir texto da página {page_number}: {e}", exc_info=True)
            return [] # Retorna lista vazia em caso de erro

    # Método evaluate_chunk (manter se ainda relevante, senão remover)
    async def evaluate_chunk(self, chunk_text: str) -> Optional[float]:
         # if self.quality_evaluator:
         #     return await self.quality_evaluator.evaluate(chunk_text)
         logger.warning("Avaliação de qualidade de chunk não implementada/configurada.")
         return None

    async def chunk(self, text: str, strategy: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """ Divide o texto usando a estratégia especificada. """
        logger.info(f"Iniciando chunking com estratégia: {strategy}, size: {chunk_size}, overlap: {chunk_overlap}")

        if not text or not text.strip():
            logger.warning("Texto vazio recebido para chunking.")
            return []

        try:
            if strategy == "semantic" or strategy == "hybrid": # Usar semântico como padrão ou para híbrido
                # Assumindo que create_semantic_chunks é síncrona
                def sync_semantic_chunk():
                    # Passe os parâmetros necessários para a função original
                    return create_semantic_chunks(
                        text,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        strategy=strategy # A função original pode usar isso internamente
                    )
                chunk_texts = await asyncio.to_thread(sync_semantic_chunk)

            elif strategy == "simple":
                # Assumindo que create_simple_chunks é síncrona
                def sync_simple_chunk():
                     return create_simple_chunks(
                          text,
                          chunk_size=chunk_size,
                          chunk_overlap=chunk_overlap
                     )
                chunk_texts = await asyncio.to_thread(sync_simple_chunk)

            # Adicionar outras estratégias aqui (ex: "header_based") se necessário
            # elif strategy == "header_based": ...

            else:
                logger.warning(f"Estratégia de chunking desconhecida: '{strategy}'. Usando 'semantic' como fallback.")
                # Copiar a lógica do 'semantic' como fallback ou lançar erro
                def sync_semantic_fallback():
                    return create_semantic_chunks(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap, strategy="semantic")
                chunk_texts = await asyncio.to_thread(sync_semantic_fallback)

            logger.info(f"Chunking com estratégia '{strategy}' gerou {len(chunk_texts)} chunks.")
            return chunk_texts

        except Exception as e:
            logger.exception(f"Erro durante o chunking com estratégia '{strategy}': {e}")
            raise RuntimeError(f"Falha no processo de chunking: {e}") from e
