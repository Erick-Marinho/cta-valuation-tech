import logging
from typing import List, Any
from langchain_core.embeddings import Embeddings
from langchain_core.pydantic_v1 import BaseModel, Extra
import time

# Importar nossa interface e implementação
from application.interfaces.embedding_provider import EmbeddingProvider as AppEmbeddingProvider # Alias para evitar conflito
# from backend.infrastructure.external_services.embedding.huggingface_embedding_provider import HuggingFaceEmbeddingProvider # Para type hint
from infrastructure.external_services.embedding.huggingface_embedding_provider import HuggingFaceEmbeddingProvider

logger = logging.getLogger(__name__)

class LangChainHuggingFaceEmbeddings(Embeddings):
    """
    Wrapper Langchain totalmente síncrono para integrar nosso HuggingFaceEmbeddingProvider assíncrono.
    
    Esta implementação usa bloqueio direto para chamar os métodos async, o que não é ideal
    mas evita problemas de compatibilidade com bibliotecas como RAGAS que esperam chamadas
    síncronas e não lidam bem com coroutines.
    """
    
    def __init__(self, provider: AppEmbeddingProvider):
        """Inicializa com o provider já instanciado."""
        self.provider = provider
        if not isinstance(provider, HuggingFaceEmbeddingProvider):
            logger.warning(f"Provider passado não é uma instância de HuggingFaceEmbeddingProvider (tipo: {type(provider)}).")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Versão síncrona bloqueante para gerar embeddings para múltiplos textos.
        Não recomendada para uso geral, apenas para compatibilidade com RAGAS/DeepEval.
        """
        import asyncio
        
        logger.debug(f"embed_documents (sync) chamado para {len(texts)} textos")
        start_time = time.time()
        
        try:
            # Criamos um novo evento loop para executar de forma síncrona
            # Isto é um anti-padrão, mas necessário para compatibilidade
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(self.provider.embed_batch(texts))
                logger.debug(f"embed_documents (sync) concluído em {time.time() - start_time:.2f}s")
                return result
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Erro em embed_documents (sync): {e}", exc_info=True)
            # Fallback para dimensão padrão em caso de erro
            dimension = getattr(self.provider.settings, 'EMBEDDING_DIMENSION', 1024)
            return [[0.0] * dimension for _ in texts]
    
    def embed_query(self, text: str) -> List[float]:
        """
        Versão síncrona bloqueante para gerar embedding para um único texto.
        Não recomendada para uso geral, apenas para compatibilidade com RAGAS/DeepEval.
        """
        import asyncio
        
        logger.debug("embed_query (sync) chamado")
        start_time = time.time()
        
        try:
            # Criamos um novo evento loop para executar de forma síncrona
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(self.provider.embed_text(text))
                logger.debug(f"embed_query (sync) concluído em {time.time() - start_time:.2f}s")
                return result
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Erro em embed_query (sync): {e}", exc_info=True)
            # Fallback para dimensão padrão em caso de erro
            dimension = getattr(self.provider.settings, 'EMBEDDING_DIMENSION', 1024) 
            return [0.0] * dimension

    # --- Métodos Síncronos REMOVIDOS ---
    # Deixamos a classe base Embeddings (herdada) tentar lidar com chamadas síncronas,
    # que por padrão tentam rodar as versões async usando o loop de eventos existente.
