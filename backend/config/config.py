"""
Configurações centralizadas para a aplicação CTA Value Tech.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from typing import Optional, List
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
    DATABASE_URL: str = Field(default=os.getenv("DATABASE_URL", ""),
                              description="Database connection URL")
    AUTO_INIT_DB: bool = False

    # Serviços externos
    API_KEY_NVIDEA: str = ""
    # API_KEY: Optional[str] = None

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
    MAX_RESULTS: int = 4
    RAG_SYSTEM_PROMPT: str = Field(
        default="""Você é um assistente prestativo. Use o contexto fornecido para responder à pergunta do usuário. Responda em português brasileiro.""",
        description="Prompt base do sistema para o RAG."
    )

    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Configurações PostgreSQL
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "vectordb"
    POSTGRES_PORT: str = "5433"
    DB_PASSWORD: Optional[str] = None

    # Configurações PGAdmin
    PGADMIN_DEFAULT_EMAIL: str = "admin@admin.com"
    PGADMIN_DEFAULT_PASSWORD: str = "pgadmin"
    PGADMIN_PORT: str = "5050"

    # Autenticação (opcional)
    API_KEY: str = "your_api_key_here"

    # Logging
    LOG_LEVEL: str = "INFO"

    # OpenAI
    OPENAI_API_KEY: Optional[str] = None

    # Configurações OpenTelemetry
    OTEL_EXPORTER_OTLP_ENDPOINT: str = Field(
        default=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
        description="OTLP Exporter endpoint (gRPC or HTTP).",
    )
    OTEL_SERVICE_NAME: str = Field(
        default=os.getenv("OTEL_SERVICE_NAME", "cta-value-tech-rag"),
        description="Service name for OpenTelemetry.",
    )

    # --- Adicionar configuração do MLflow Tracking URI ---
    MLFLOW_TRACKING_URI: Optional[str] = Field(
        default=None, # Pydantic lerá do .env se presente
        description="URI for the MLflow Tracking Server."
    )
    # -----------------------------------------------------

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
