"""
Módulo de embedders para geração de vetores a partir de textos.
"""
from processors.embedders.EmbedderBase import EmbedderInterface
from processors.embedders.HuggingFaceEmbedder import HuggingFaceEmbedder

__all__ = ['EmbedderInterface', 'HuggingFaceEmbedder'] 