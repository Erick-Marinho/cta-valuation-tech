"""
Extratores de texto de diferentes tipos de documentos.
"""

from .pdf_extractor import PDFExtractor
from .text_extractor import TextExtractor

__all__ = ['PDFExtractor', 'TextExtractor']