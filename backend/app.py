"""
Ponto de entrada principal da aplicação CTA Value Tech.
"""
import time
import uvicorn
import logging
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from utils.metrics_prometheus import HTTP_REQUESTS_TOTAL, REQUEST_LATENCY, update_system_metrics
from utils.telemetry import setup_telemetry
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Importações dos módulos da aplicação
from core.config import get_settings
from api.router import main_router
from db.schema import setup_database, is_database_healthy
from utils.logging import configure_logging
from utils.metrics_prometheus import create_metrics_app, init_app_info

# Configurar logging
configure_logging()
logger = logging.getLogger(__name__)

# Obter configurações
settings = get_settings()

# Definir lifespan da aplicação
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerenciador de contexto para o ciclo de vida da aplicação.
    """
    try:
        # Inicializar OpenTelemetry antes de tudo
        setup_telemetry("cta-value-tech")
        logger.info("OpenTelemetry inicializado com sucesso")
        
        # Configurar banco de dados
        logger.info("Inicializando banco de dados...")
        setup_database()
        
        if not is_database_healthy():
            logger.error("Banco de dados não está saudável!")
        else:
            logger.info("Banco de dados inicializado com sucesso!")
            
    except Exception as e:
        logger.error(f"Erro ao inicializar banco de dados: {e}")
    
    logger.info("Application is starting...")
    yield
    logger.info("Application is shutting down...")

# Criar aplicação FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    description="API para valoração de tecnologias relacionadas ao Patrimônio Genético Nacional e Conhecimentos Tradicionais Associados",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Instrumentar a aplicação para OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

#Criar app de métricas e inicializar info
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
    status_code = 500 # Default para caso de erro inesperado antes da resposta
    
    # Processar a requisição
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        logger.exception("Erro não tratado durante a requisição")
        status_code = 500
        raise # Re-lançar exceção para ser tratada pelo FastAPI
    finally:
        # Métricas que são registradas mesmo em caso de erro
        endpoint = request.url.path
        method = request.method
        
    # 1. Incrementar contador de requisições
        HTTP_REQUESTS_TOTAL.labels(
            method=method, 
            endpoint=endpoint, 
            status=str(status_code)
        ).inc()
    
    # 2. Registrar latência
        request_time = time.time() - start_time
        REQUEST_LATENCY.labels(
            method=method, 
            endpoint=endpoint
        ).observe(request_time)
    
    return response

# Incluir rotas da API
app.include_router(main_router)

# Iniciar aplicação se executada diretamente
if __name__ == "__main__":
    port = settings.PORT
    logger.info(f"Iniciando aplicação na porta {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)