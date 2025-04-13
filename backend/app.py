"""
Ponto de entrada principal da aplicação CTA Value Tech.
"""

import time
import uvicorn
import logging
import asyncpg
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from infrastructure.metrics.prometheus.metrics_prometheus import (
    HTTP_REQUESTS_TOTAL,
    REQUEST_LATENCY,
    update_system_metrics,
    create_metrics_app,
    init_app_info,
)
from infrastructure.telemetry.opentelemetry import initialize_telemetry
from infrastructure.logging.config import configure_logging
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Importações dos módulos da aplicação
from config.config import get_settings
from api.router import main_router
# TODO: Refatorar db.schema para usar asyncpg
# from db.schema import setup_database, is_database_healthy

# --- Importações SQLAlchemy/SQLModel Async ---
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
# -------------------------------------------

# Configurar logging
configure_logging()
logger = logging.getLogger(__name__)

# Obter configurações
settings = get_settings()

# Variável global para o pool (ou usar app.state diretamente)
# DB_POOL: asyncpg.Pool = None # Opcional, app.state é preferível

# --- Gerenciador de Ciclo de Vida com Engine Async ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Código a ser executado ANTES da aplicação iniciar
    logger.info("Iniciando aplicação...")
    settings = get_settings()

    # Criar Async Engine SQLAlchemy
    logger.info("Criando Async Engine SQLAlchemy...")
    # Garantir que a URL use o driver asyncpg
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    try:
        # echo=True é útil para debug, mostra SQL gerado
        engine = create_async_engine(db_url, echo=settings.DEBUG, future=True)
        # Armazenar a engine no estado da aplicação para ser acessada pelas dependências
        app.state.db_engine = engine
        logger.info("Async Engine SQLAlchemy criada com sucesso.")

        # Testar conexão (opcional, mas recomendado)
        async with engine.connect() as conn:
             logger.info("Conexão inicial com o banco de dados estabelecida.")

    except Exception as e:
        logger.exception(f"Falha ao criar Async Engine ou conectar ao banco: {e}")
        # Você pode querer impedir a inicialização se o DB não estiver disponível
        raise RuntimeError(f"Falha na inicialização do banco de dados: {e}") from e

    # Inicializar OpenTelemetry
    try:
        initialize_telemetry(service_name=settings.OTEL_SERVICE_NAME, otlp_endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
        logger.info("OpenTelemetry inicializado com sucesso")
    except Exception as e:
        logger.error(f"Falha ao inicializar OpenTelemetry: {e}")

    yield # Aplicação roda aqui

    # Código a ser executado APÓS a aplicação parar
    logger.info("Encerrando aplicação...")
    if hasattr(app.state, 'db_engine') and app.state.db_engine:
        logger.info("Dispondo da Async Engine SQLAlchemy...")
        await app.state.db_engine.dispose()
        logger.info("Async Engine disposta.")


# Criar aplicação FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    description="API para valoração de tecnologias relacionadas ao Patrimônio Genético Nacional e Conhecimentos Tradicionais Associados",
    version=settings.APP_VERSION,
    lifespan=lifespan, # <-- Usar o lifespan definido acima
    docs_url="/docs",
    redoc_url="/redoc",
)

# Criar app de métricas e inicializar info
metrics_app = create_metrics_app()
init_app_info(settings.APP_NAME, settings.APP_VERSION)
app.mount("/metrics", metrics_app)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):

    # Atualizar métricas do sistema
    update_system_metrics()

    # Registrar início da requisição
    start_time = time.time()
    status_code = 500  # Default para caso de erro inesperado antes da resposta

    # Processar a requisição
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        logger.exception("Erro não tratado durante a requisição")
        status_code = 500
        raise  # Re-lançar exceção para ser tratada pelo FastAPI
    finally:
        # Métricas que são registradas mesmo em caso de erro
        endpoint = request.url.path
        method = request.method

        # 1. Incrementar contador de requisições
        HTTP_REQUESTS_TOTAL.labels(
            method=method, endpoint=endpoint, status=str(status_code)
        ).inc()

        # 2. Registrar latência
        request_time = time.time() - start_time
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(request_time)

    return response


# Incluir rotas da API
app.include_router(main_router)

# Instrumentar a aplicação DEPOIS de incluir as rotas
FastAPIInstrumentor.instrument_app(app)

# Iniciar aplicação se executada diretamente
if __name__ == "__main__":
    port = settings.PORT
    logger.info(f"Iniciando aplicação na porta {port}...")
    # host="0.0.0.0" é importante para Docker, mantenha
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=settings.DEBUG) # Usar app:app para reload
