import logging
from typing import Dict, Any

# --- Imports de Telemetria ---
# (Assumindo que utils.telemetry existe e está acessível)
from utils.telemetry import get_tracer
from opentelemetry.trace import Status, StatusCode
# ------------------------------

logger = logging.getLogger(__name__)

# Cache compartilhado para instâncias de providers dentro da execução da CLI
_provider_cache: Dict[str, Any] = {}

def get_cached_provider(provider_key: str, factory_func):
    """
    Obtém ou cria uma instância de provider do cache para a execução atual da CLI.
    """
    # Obter tracer para esta função utilitária
    # NOTA: Telemetria deve ser inicializada antes desta função ser chamada.
    tracer = get_tracer(__name__)
    with tracer.start_as_current_span("cli.get_cached_provider") as span:
        span.set_attribute("provider.key", provider_key)
        if provider_key not in _provider_cache:
            span.set_attribute("provider.cache_hit", False)
            logger.info(f"Cache miss. Criando nova instância para provider: {provider_key}")
            try:
                 instance = factory_func() # Chama a função que cria a instância real
                 _provider_cache[provider_key] = instance
                 span.set_status(Status(StatusCode.OK))
                 logger.info(f"Instância de {provider_key} criada e cacheada.")
            except Exception as e:
                 logger.error(f"Erro ao criar instância do provider {provider_key}: {e}", exc_info=True)
                 span.record_exception(e)
                 span.set_status(Status(StatusCode.ERROR, f"Falha ao criar instância do provider {provider_key}"))
                 raise # Relança a exceção para quem chamou
        else:
            span.set_attribute("provider.cache_hit", True)
            span.set_status(Status(StatusCode.OK))
            logger.debug(f"Cache hit. Retornando instância cacheada para provider: {provider_key}")
        return _provider_cache[provider_key]

def clear_provider_cache():
    """ Limpa o cache de providers (útil para testes ou reinicialização). """
    global _provider_cache
    logger.debug("Limpando cache de providers da CLI.")
    _provider_cache = {}
