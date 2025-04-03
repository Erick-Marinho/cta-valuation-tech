"""
Configurações centralizadas para a aplicação CTA Value Tech.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from typing import Optional
import os

class Settings(BaseSettings):
    """
    Configurações da aplicação com valores padrão e validação via Pydantic.
    
    Atributos:
        APP_NAME: Nome da aplicação
        APP_VERSION: Versão da aplicação
        DEBUG: Modo de depuração
        DATABASE_URL: URL de conexão com o banco de dados
        AUTO_INIT_DB: Inicialização automática do banco de dados
        API_KEY_NVIDEA: Chave de API para NVIDIA
        EMBEDDING_MODEL: Modelo de embeddings a ser utilizado
        EMBEDDING_DIMENSION: Dimensão dos embeddings
        CHUNK_SIZE: Tamanho padrão de chunks de texto
        CHUNK_OVERLAP: Sobreposição padrão entre chunks
        PORT: Porta do servidor
        CORS_ORIGINS: Origens permitidas para CORS
    """
    # Configurações da aplicação
    APP_NAME: str = "CTA Value Tech"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database
    # Verifica se está rodando em Docker ou localhost
    DATABASE_URL: str = "postgresql://postgres:postgres@postgres:5433/vectordb"
    AUTO_INIT_DB: bool = False
    
    # Serviços externos
    API_KEY_NVIDEA: str = ""
    #API_KEY: Optional[str] = None
    
    # LLM
    LLM_MODEL: str = "meta/llama3-70b-instruct"
    
    # Configuração do modelo de embeddings
    EMBEDDING_MODEL: str = "intfloat/multilingual-e5-large-instruct"
    EMBEDDING_DIMENSION: int = 1024
    USE_GPU: bool = False
    
    # Configuração de processamento de texto
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    
    # Servidor
    PORT: int = 8000
    CORS_ORIGINS: list = ["*"]
    
    # RAG
    VECTOR_SEARCH_WEIGHT: float = 0.7  # Peso da busca vetorial vs. textual
    TEXT_SEARCH_WEIGHT: float = 0.3    # Complemento do peso vetorial
    SEARCH_THRESHOLD: float = 0.5      # Limiar mínimo de similaridade
    MAX_RESULTS: int = 10  
    
    #Configurações PostgreSQL
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "vectordb"
    POSTGRES_PORT: str = "5433"

    # Configurações PGAdmin
    PGADMIN_DEFAULT_EMAIL: str = "admin@admin.com"
    PGADMIN_DEFAULT_PASSWORD: str = "pgadmin"
    PGADMIN_PORT: str = "5050"
    
    # Autenticação (opcional)
    API_KEY: str = "your_api_key_here"
    
    #Logging
    LOG_LEVEL: str = "INFO"
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    
    # Configurações OpenTelemetry
    OTEL_EXPORTER_OTLP_ENDPOINT: str = Field(
        default=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
        description="OTLP Exporter endpoint (gRPC or HTTP)."
    )
    OTEL_SERVICE_NAME: str = Field(
        default=os.getenv("OTEL_SERVICE_NAME", "cta-value-tech-rag"),
        description="Service name for OpenTelemetry."
    )
    
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