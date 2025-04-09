"""
Chunker simples para divisão de texto em partes de tamanho fixo.
"""

import logging
from typing import List
from langchain_text_splitters import CharacterTextSplitter
from ..normalizers.text_normalizer import normalize_text

logger = logging.getLogger(__name__)


def create_simple_chunks(
    text: str, chunk_size: int = 800, chunk_overlap: int = 100
) -> List[str]:
    """
    Divide o texto em chunks de tamanho fixo, sem considerar a estrutura semântica.
    Útil para documentos sem estrutura clara ou para processamento rápido.

    Args:
        text (str): Texto completo do documento
        chunk_size (int): Tamanho máximo de cada chunk
        chunk_overlap (int): Sobreposição entre chunks consecutivos

    Returns:
        list: Lista de chunks de texto
    """
    # Verificar se o texto está vazio
    if not text or not text.strip():
        logger.warning("Texto vazio fornecido para chunking simples")
        return []

    logger.info(f"Iniciando chunking simples. Tamanho do texto: {len(text)} caracteres")

    # Criar splitter para divisão por caracteres
    splitter = CharacterTextSplitter(
        separator="\n\n",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )

    # Dividir o texto em chunks
    chunks = splitter.split_text(text)

    # Normalizar os chunks
    normalized_chunks = [normalize_text(chunk) for chunk in chunks]

    # Filtrar chunks vazios ou muito pequenos
    filtered_chunks = [chunk for chunk in normalized_chunks if len(chunk.strip()) > 50]

    logger.info(f"Chunking simples concluído. Gerados {len(filtered_chunks)} chunks")

    return filtered_chunks
