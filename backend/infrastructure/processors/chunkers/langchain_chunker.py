import asyncio
import logging
from typing import List

# Importar Interface da Aplicação
from application.interfaces.chunker import Chunker

# Importar implementações concretas (dos novos locais na infraestrutura)
# Ajuste o caminho exato se necessário
from .semantic_chunker import create_semantic_chunks
# Importe o simple_chunker também se for mantê-lo
from .simple_chunker import create_simple_chunks

logger = logging.getLogger(__name__)

class LangchainChunker(Chunker):
    """ Implementação de Chunker usando funções baseadas em Langchain (ou similar). """

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
