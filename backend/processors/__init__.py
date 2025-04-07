"""
Processadores para textos e documentos.

Este módulo contém componentes para processamento de textos e documentos,
incluindo extração, chunking e normalização.
"""

from .extractors import PDFExtractor, TextExtractor
from .chunkers import create_semantic_chunks, create_simple_chunks
from .normalizers import (
    normalize_text,
    clean_text_for_embedding,
    clean_query,
    extract_keywords,
)

__all__ = [
    "PDFExtractor",
    "TextExtractor",
    "create_semantic_chunks",
    "create_simple_chunks",
    "normalize_text",
    "clean_text_for_embedding",
    "clean_query",
    "extract_keywords",
]
