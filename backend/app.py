"""
Ponto de entrada principal da aplicação CTA Value Tech.
"""
import time
import uvicorn
import logging
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from utils.metrics_prometheus import HTTP_REQUESTS_TOTAL, REQUEST_LATENCY, update_system_metrics, create_metrics_app, init_app_info

# Importações dos módulos da aplicação
from core.config import get_settings
from api.router import main_router
from db.schema import setup_database, is_database_healthy
from utils.logging import configure_logging

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
    start_time = time.time()
    
    # Atualizar métricas do sistema
    update_system_metrics()
    
    # Processar a requisição
    response = await call_next(request)
    
    # Registrar métricas
    endpoint = request.url.path
    method = request.method
    status = response.status_code
    
    # Registrar contador de requisições
    HTTP_REQUESTS_TOTAL.labels(
        method=method, endpoint=endpoint, status=status
    ).inc()
    
    # Registrar latência
    REQUEST_LATENCY.labels(
        method=method, endpoint=endpoint
    ).observe(time.time() - start_time)
    
    return response

# Incluir rotas da API
app.include_router(main_router)

# Iniciar aplicação se executada diretamente
if __name__ == "__main__":
    port = settings.PORT
    logger.info(f"Iniciando aplicação na porta {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)