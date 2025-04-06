"""
Interface para serviços de embedding.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class EmbedderInterface(ABC):
    """
    Interface para padronizar diferentes implementações de modelos de embedding.
    
    Fornece um contrato que todas as implementações de embedders devem seguir,
    permitindo a substituição transparente entre diferentes backends.
    """
    
    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """
        Gera um embedding para um texto único.
        
        Args:
            text: Texto para gerar embedding
            
        Returns:
            list: Vetor de embedding
        """
        pass
    
    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Gera embeddings para múltiplos textos em lote.
        
        Args:
            texts: Lista de textos para gerar embeddings
            
        Returns:
            list: Lista de vetores de embedding
        """
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """
        Retorna a dimensão dos embeddings gerados pelo modelo.
        
        Returns:
            int: Dimensão dos vetores de embedding
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Retorna informações sobre o modelo de embeddings.
        
        Returns:
            dict: Informações do modelo (nome, dimensão, etc.)
        """
        pass
