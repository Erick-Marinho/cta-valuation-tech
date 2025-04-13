import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

# Importar exceções customizadas
try:
    # Usar ValidationError que está definido no seu arquivo
    from shared.exceptions import CoreException, LLMServiceError, ValidationError, DatabaseError, ResourceNotFoundError, ServiceUnavailableError
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("Módulo 'shared.exceptions' ou exceções customizadas não encontradas. Definindo placeholders.")
    class CoreException(Exception): pass
    class LLMServiceError(CoreException): pass
    class ValidationError(CoreException): pass # Nome corrigido
    class DatabaseError(CoreException): pass
    class ResourceNotFoundError(CoreException): pass
    class ServiceUnavailableError(CoreException): pass


logger = logging.getLogger(__name__)

class CustomErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware para capturar exceções conhecidas e desconhecidas,
    retornando respostas JSON padronizadas.
    """
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        try:
            response = await call_next(request)
            return response

        # --- Captura de Exceções Específicas ---

        # except ValidationException as exc: # <-- Linha antiga comentada/removida
        except ValidationError as exc: # <-- Linha corrigida
            logger.warning(f"Erro de validação da aplicação: {exc}", exc_info=False)
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": f"Erro de validação: {exc}"},
            )
        except ValueError as exc:
             logger.warning(f"ValueError não tratado: {exc}", exc_info=False)
             return JSONResponse(
                 status_code=status.HTTP_400_BAD_REQUEST,
                 content={"detail": f"Valor inválido fornecido: {exc}"},
             )
        except ResourceNotFoundError as exc: # Adicionado handler
             logger.warning(f"Recurso não encontrado: {exc}", exc_info=False)
             return JSONResponse(
                 status_code=status.HTTP_404_NOT_FOUND,
                 content={"detail": str(exc)},
             )
        except LLMServiceError as exc:
            logger.error(f"Erro no serviço LLM: {exc}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": f"Serviço de linguagem indisponível: {exc}"},
            )
        except ServiceUnavailableError as exc: # Adicionado handler
             logger.error(f"Serviço externo indisponível: {exc}", exc_info=True)
             return JSONResponse(
                 status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                 content={"detail": f"Serviço indisponível: {exc}"},
             )
        except DatabaseError as exc:
            logger.error(f"Erro de banco de dados: {exc}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, # Pode ser 500 também, dependendo do caso
                content={"detail": f"Erro no serviço de banco de dados: {exc}"},
            )
        except CoreException as exc:
            logger.error(f"Erro Core da aplicação: {exc}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": f"Erro interno na aplicação: {exc}"},
            )

        # --- Captura Genérica (Fallback) ---

        except Exception as exc:
            logger.exception("Erro inesperado não tratado:")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Ocorreu um erro interno inesperado no servidor."},
            )
