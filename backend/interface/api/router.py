"""
Configuração central de rotas da API.
"""

from fastapi import APIRouter

# from .endpoints import chat, document, health # <-- Usar import relativo é mais comum aqui
# Ou, se preferir absoluto:
from interface.api.endpoints import chat, document, health # <-- Import absoluto (funciona também)

# Criar roteador principal
main_router = APIRouter()

# Incluir roteadores de endpoints
main_router.include_router(chat.router)
main_router.include_router(document.router)
main_router.include_router(health.router)


# Rota raiz
@main_router.get("/")
async def root():
    """
    Rota raiz da API.
    """
    return {
        "message": "API de Valoração de Tecnologias com PostgreSQL - CTA Value Tech",
        "version": "1.0.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
    }
