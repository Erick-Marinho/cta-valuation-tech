"""
Configurações centralizadas para a aplicação CTA Value Tech.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    """
    Configurações da aplicação com valores padrão e validação via Pydantic.
    
    Atributos:
        APP_NAME: Nome da aplicação
        APP_VERSION: Versão da aplicação
        DEBUG: Modo de depuração
        DATABASE_URL: URL de conexão com o banco de dados
        AUTO_INIT_DB: 
        API_KEY_NVIDEA: Chave de API para NVIDIA
        EMBEDDING_MODEL: Modelo de embeddings a ser utilizado
        EMBEDDING_DIMENSION: Dimensão dos embeddings
        CHUNK_SIZE: Tamanho padrão de chunks de texto
        CHUNK_OVERLAP: Sobreposição padrão entre chunks
        PORT: Porta do servidor
        CORS_ORIGINS: Origens permitidas para CORS
    """
    APP_NAME: str = "CTA Value Tech"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5433/vectordb"
    AUTO_INIT_DB: bool = False  
    
    # Serviços externos
    API_KEY_NVIDEA: str
    API_KEY: Optional[str] = None  
    
    # Embeddings
    EMBEDDING_MODEL: str = "intfloat/multilingual-e5-large-instruct"
    EMBEDDING_DIMENSION: int = 1024
    USE_GPU: bool = True  
    
    # Processamento de texto
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    
    # Servidor
    PORT: int = 8000
    CORS_ORIGINS: list = ["*"]
    
    # RAG
    VECTOR_SEARCH_WEIGHT: float = 0.7  # Peso da busca vetorial vs. textual
    TEXT_SEARCH_WEIGHT: float = 0.3    # Complemento do peso vetorial
    SEARCH_THRESHOLD: float = 0.6      # Limiar mínimo de similaridade
    MAX_RESULTS: int = 5               # Número máximo de resultados na busca
    
    #Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

@lru_cache
def get_settings() -> Settings:
    """
    Retorna as configurações da aplicação.
    Utiliza cache para evitar recarregar a cada chamada.
    
    Returns:
        Settings: Configurações da aplicação
    """
    return Settings()