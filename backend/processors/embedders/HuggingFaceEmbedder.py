"""
Implementação do embedder usando HuggingFace.
"""
import logging
from typing import List, Dict, Any
from langchain_huggingface import HuggingFaceEmbeddings
from processors.embedders.EmbedderBase import EmbedderInterface
from processors.normalizers.text_normalizer import clean_text_for_embedding

logger = logging.getLogger(__name__)

class HuggingFaceEmbedder(EmbedderInterface):
    """
    Implementação de embeddings usando a biblioteca HuggingFace.
    """
    
    def __init__(self, model_name: str, device: str = "cpu"):
        """
        Inicializa o embedder HuggingFace.
        
        Args:
            model_name: Nome do modelo de embeddings do HuggingFace
            device: Dispositivo para execução do modelo ('cpu' ou 'cuda')
        """
        self.model_name = model_name
        self.device = device
        
        logger.info(f"Inicializando modelo de embeddings: {model_name} no dispositivo: {device}")
        
        try:
            self.model = HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={"device": device},
                encode_kwargs={"normalize_embeddings": True}
            )
            
            # Verificar dimensão do modelo
            test_text = "verificação de dimensão"
            test_embedding = self.model.embed_query(test_text)
            self._dimension = len(test_embedding)
            
            logger.info(f"Modelo de embeddings '{model_name}' inicializado. Dimensão: {self._dimension}")
            
        except Exception as e:
            logger.error(f"Falha crítica ao inicializar modelo de embeddings '{model_name}': {e}", exc_info=True)
            raise RuntimeError(f"Falha ao inicializar modelo de embeddings: {e}") from e
    
    def embed_query(self, text: str) -> List[float]:
        """
        Gera embedding para um texto único.
        
        Args:
            text: Texto para gerar embedding
            
        Returns:
            list: Vetor de embedding
        """
        if not text or not text.strip():
            logger.warning("Tentativa de embedding para texto vazio.")
            return [0.0] * self._dimension
        
        clean_text = clean_text_for_embedding(text).lower()
        
        try:
            # embedding = self.model.embed_query(clean_text)
            embedding = self.model.embed_query(text)
            return embedding
        except Exception as e:
            logger.error(f"Erro ao gerar embedding para texto: '{clean_text[:50]}...': {e}", exc_info=True)
            return [0.0] * self._dimension
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Gera embeddings para múltiplos textos em lote.
        
        Args:
            texts: Lista de textos para gerar embeddings
            
        Returns:
            list: Lista de vetores de embedding
        """
        if not texts:
            return []
        
        clean_texts = []
        empty_indices = set()
        
        for i, text in enumerate(texts):
            if not text or not text.strip():
                empty_indices.add(i)
                clean_texts.append("")
            else:
                clean_texts.append(clean_text_for_embedding(text).lower())
        
        try:
            # Primeiro, filtrar textos vazios para evitar erros no modelo
            filtered_texts = [t for i, t in enumerate(clean_texts) if i not in empty_indices]
            
            # Se todos os textos forem vazios, retornar lista de vetores zero
            if not filtered_texts:
                return [[0.0] * self._dimension for _ in range(len(texts))]
            
            # Gerar embeddings para textos não vazios
            generated_embeddings = self.model.embed_documents(texts)
            # generated_embeddings = self.model.embed_documents(filtered_texts)
            
            # Recompor a lista final com vetores zero para textos vazios
            final_embeddings = []
            gen_idx = 0
            
            for i in range(len(texts)):
                if i in empty_indices:
                    final_embeddings.append([0.0] * self._dimension)
                else:
                    final_embeddings.append(generated_embeddings[gen_idx])
                    gen_idx += 1
            
            return final_embeddings
            
        except Exception as e:
            logger.error(f"Erro ao gerar embeddings em lote: {e}", exc_info=True)
            return [[0.0] * self._dimension for _ in range(len(texts))]
    
    def get_dimension(self) -> int:
        """
        Retorna a dimensão dos embeddings gerados pelo modelo.
        
        Returns:
            int: Dimensão dos vetores de embedding
        """
        return self._dimension
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Retorna informações sobre o modelo de embeddings.
        
        Returns:
            dict: Informações do modelo
        """
        return {
            "name": self.model_name,
            "dimension": self._dimension,
            "device": self.device,
            "type": "huggingface"
        } 