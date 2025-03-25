"""
Configurações centralizadas para a aplicação CTA Value Tech.
"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
from pydantic import Field

class Settings(BaseSettings):
    """
    Configurações da aplicação com valores padrão e validação via Pydantic.
    
    Atributos:
        APP_NAME: Nome da aplicação
        APP_VERSION: Versão da aplicação
        DEBUG: Modo de depuração
        DATABASE_URL: URL de conexão com o banco de dados
        API_KEY_NVIDEA: Chave de API para NVIDIA
        EMBEDDING_MODEL: Modelo de embeddings a ser utilizado
        EMBEDDING_DIMENSION: Dimensão dos embeddings
        CHUNK_SIZE: Tamanho padrão de chunks de texto
        CHUNK_OVERLAP: Sobreposição padrão entre chunks
        PORT: Porta do servidor
        CORS_ORIGINS: Origens permitidas para CORS
    """
    APP_NAME: str = os.getenv("APP_NAME")
    APP_VERSION: str = os.getenv("APP_VERSION")
    DEBUG: bool = os.getenv("DEBUG")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    AUTO_INIT_DB: bool = os.getenv("AUTO_INIT_DB")
    
    # Serviços externos
    API_KEY_NVIDEA: str
    API_KEY: Optional[str] = None
    
    # Embeddings
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL")
    EMBEDDING_DIMENSION: int = os.getenv("EMBEDDING_DIMENSION")
    USE_GPU: bool = os.getenv("USE_GPU")
    
    # Processamento de texto
    CHUNK_SIZE: int = os.getenv("CHUNK_SIZE")
    CHUNK_OVERLAP: int = os.getenv("CHUNK_OVERLAP")
    
    # Servidor
    PORT: int = os.getenv("PORT")
    CORS_ORIGINS: list = ["*"]
    
    # RAG
    VECTOR_SEARCH_WEIGHT: float = 0.7  # Peso da busca vetorial vs. textual
    TEXT_SEARCH_WEIGHT: float = 0.3    # Complemento do peso vetorial
    SEARCH_THRESHOLD: float = 0.6      # Limiar mínimo de similaridade
    MAX_RESULTS: int = 5               # Número máximo de resultados na busca

    # LANGSMITH
    LANGSMITH_TRACING: str = Field(default="false")
    LANGSMITH_ENDPOINT: str = Field(default="https://api.smith.langchain.com")
    LANGSMITH_API_KEY: str = Field(default="")
    LANGSMITH_PROJECT: str = Field(default="default")
    OPENAI_API_KEY: str = Field(default="")
    
    #Logging
    LOG_LEVEL: str = "INFO"  # Adicionado
    
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