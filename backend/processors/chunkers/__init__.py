"""
Chunkers para divisão de texto em partes processáveis.
"""

from .semantic_chunker import create_semantic_chunks
from .simple_chunker import create_simple_chunks
from .nltk_chunker import create_nltk_chunks
__all__ = ['create_semantic_chunks', 'create_simple_chunks', 'create_nltk_chunks']