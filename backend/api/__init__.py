"""
Módulo de API para o CTA Value Tech.

Este módulo contém os endpoints e configurações da API REST,
incluindo rotas para chat, documentos e monitoramento.
"""

from .router import main_router

__all__ = ["main_router"]
