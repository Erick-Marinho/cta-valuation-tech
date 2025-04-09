# utils/telemetry.py
"""
Configuração e utilidades para o OpenTelemetry.

Este módulo configura o rastreamento distribuído usando OpenTelemetry,
permitindo acompanhar o fluxo de requisições através dos componentes do sistema.
"""
import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.sampling import ParentBased, ALWAYS_ON
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
import os

logger = logging.getLogger(__name__)

# Flag para garantir que a configuração seja feita apenas uma vez
_telemetry_initialized = False


def setup_telemetry(service_name="cta-value-tech"):
    """
    Configura o OpenTelemetry para o serviço.

    Esta função inicializa o OpenTelemetry para rastreamento distribuído,
    configurando um exportador para enviar os dados para o Jaeger.

    Args:
        service_name: Nome do serviço para identificação nos traces

    Returns:
        tracer: Um tracer configurado para criar spans
    """
    from config.config import get_settings

    global _telemetry_initialized
    if _telemetry_initialized:
        logger.warning("Tentativa de configurar OpenTelemetry mais de uma vez.")
        return

    try:
        settings = get_settings()
        # 1. Obter configurações
        service_name = settings.OTEL_SERVICE_NAME
        otlp_endpoint = settings.OTEL_EXPORTER_OTLP_ENDPOINT

        # 2. Criar recurso identificando o serviço
        resource = Resource(attributes={SERVICE_NAME: service_name})

        # 3. Configurar Sampler
        sampler = ParentBased(ALWAYS_ON)

        # 4. Configurar Provedor de Tracer (passando o sampler)
        provider = TracerProvider(resource=resource, sampler=sampler)

        # 5. Configurar Exportador OTLP (gRPC)
        #    A biblioteca lida com `insecure` baseado no schema da URL (http vs https)
        #    Se precisar de configuração explícita (ex: certificados), adicione aqui.
        logger.info(f"Configurando OTLP Exporter para o endpoint gRPC: {otlp_endpoint}")
        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint
        )  # Usa o endpoint da config

        # Criar processador para exportar spans em batch
        span_processor = BatchSpanProcessor(otlp_exporter)

        # Adicionar processador ao provedor
        provider.add_span_processor(span_processor)

        # Definir provedor global
        trace.set_tracer_provider(provider)

        _telemetry_initialized = True
        logger.info(
            f"OpenTelemetry configurado com sucesso para o serviço '{service_name}'"
        )

    except Exception as e:
        logger.exception(f"Erro ao configurar OpenTelemetry: {str(e)}")
        # Retornar um tracer noop que não fará nada, evitando erros
        return trace.get_tracer(__name__)


def get_tracer(name):
    """
    Obtém um tracer para o módulo especificado.

    Args:
        name: Nome do módulo ou componente

    Returns:
        Um tracer para criar spans
    """
    return trace.get_tracer(name)
