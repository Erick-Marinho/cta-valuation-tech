"""
Adaptador para embeddings do HuggingFace.
"""
import logging
from typing import List, Dict, Any, Optional
from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)

class HuggingFaceEmbeddingAdapter:
    """
    Adaptador para modelos de embedding do HuggingFace.
    
    Este adaptador encapsula a biblioteca LangChain para HuggingFace,
    proporcionando uma interface consistente independente da implementação.
    """
    
    def __init__(self, model_name: str = "intfloat/multilingual-e5-large-instruct", 
                device: str = "cuda", normalize: bool = True):
        """
        Inicializa o adaptador de embeddings.
        
        Args:
            model_name: Nome do modelo de embeddings no HuggingFace
            device: Dispositivo para execução ("cpu" ou "cuda")
            normalize: Se True, normaliza os embeddings (recomendado)
        """
        self.model_name = model_name
        self.device = device
        self.normalize = normalize
        self._initialize_model()
    
    def _initialize_model(self) -> None:
        """
        Inicializa o modelo de embeddings.
        """
        try:
            logger.info(f"Inicializando modelo de embeddings {self.model_name} no dispositivo {self.device}")
            
            self.model = HuggingFaceEmbeddings(
                model_name=self.model_name,
                model_kwargs={"device": self.device},
                encode_kwargs={"normalize_embeddings": self.normalize}
            )
            
            # Testar modelo com um texto simples
            _ = self.embed_text("teste de inicialização")
            
            logger.info(f"Modelo de embeddings inicializado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar modelo de embeddings: {e}")
            raise
    
    def embed_text(self, text: str) -> List[float]:
        """
        Gera embedding para um texto.
        
        Args:
            text: Texto para gerar embedding
            
        Returns:
            list: Vetor de embedding
        """
        try:
            if not text or not text.strip():
                logger.warning("Tentativa de embedding para texto vazio")
                # Retornar um vetor zerado
                # O tamanho do vetor depende do modelo, fazer um teste primeiro
                test_embedding = self.model.embed_query("teste")
                return [0.0] * len(test_embedding)
            
            return self.model.embed_query(text)
            
        except Exception as e:
            logger.error(f"Erro ao gerar embedding: {e}")
            raise
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Gera embeddings para múltiplos textos.
        
        Args:
            texts: Lista de textos para gerar embeddings
            
        Returns:
            list: Lista de vetores de embedding
        """
        try:
            if not texts:
                return []
            
            # Filtrar textos vazios
            valid_texts = [text for text in texts if text and text.strip()]
            if not valid_texts:
                return []
            
            return self.model.embed_documents(valid_texts)
            
        except Exception as e:
            logger.error(f"Erro ao gerar embeddings em lote: {e}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Retorna informações sobre o modelo de embeddings.
        
        Returns:
            dict: Informações do modelo
        """
        # Calcular a dimensão do embedding
        test_embedding = self.embed_text("dimensão de teste")
        embedding_dim = len(test_embedding)
        
        return {
            "model_name": self.model_name,
            "device": self.device,
            "normalize_embeddings": self.normalize,
            "embedding_dimension": embedding_dim,
            "library": "langchain_huggingface"
        }