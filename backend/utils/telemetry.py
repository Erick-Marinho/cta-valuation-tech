# utils/telemetry.py
"""
Configuração e utilidades para o OpenTelemetry.

Este módulo configura o rastreamento distribuído usando OpenTelemetry,
permitindo acompanhar o fluxo de requisições através dos componentes do sistema.
"""
import logging
import os
from typing import Optional

# OpenTelemetry Imports
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.sampling import ParentBased, ALWAYS_ON
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as GRPCSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME as ResourceAttributesServiceName, Resource

logger = logging.getLogger(__name__)

_tracer_provider: Optional[TracerProvider] = None

def initialize_telemetry(service_name: str, otlp_endpoint: Optional[str] = None):
    """
    Configura e inicializa o OpenTelemetry para Tracing (e opcionalmente Metrics).

    Args:
        service_name: Nome do serviço a ser reportado (ex: 'rag-api', 'rag-script').
        otlp_endpoint: Endpoint do coletor OTLP (ex: 'http://tempo:4317').
                       Se None, tentará obter da variável de ambiente OTEL_EXPORTER_OTLP_ENDPOINT
                       ou usará ConsoleSpanExporter como fallback.
    """
    global _tracer_provider
    if _tracer_provider:
        logger.warning("Tentativa de inicializar telemetria múltiplas vezes.")
        return

    try:
        resource = Resource(attributes={
            ResourceAttributesServiceName: service_name
        })

        # --- Configuração do Tracer ---
        _tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(_tracer_provider)

        actual_otlp_endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

        if actual_otlp_endpoint:
            logger.info(f"Configurando OTLP gRPC Span Exporter para: {actual_otlp_endpoint}")
            # Usar insecure=True se o endpoint não for HTTPS ou não tiver certificado válido
            # A opção padrão é verificar certificados
            exporter = GRPCSpanExporter(
                endpoint=actual_otlp_endpoint,
                # insecure=True # Descomente se necessário (ex: localhost sem TLS)
            )
            span_processor = BatchSpanProcessor(exporter)
        else:
            logger.warning("Endpoint OTLP não configurado. Usando ConsoleSpanExporter.")
            exporter = ConsoleSpanExporter() # Fallback para console se não houver endpoint
            span_processor = BatchSpanProcessor(exporter)

        _tracer_provider.add_span_processor(span_processor)
        logger.info(f"OpenTelemetry Tracing inicializado para serviço: '{service_name}'")

    except Exception as e:
        logger.error(f"Falha ao inicializar OpenTelemetry: {e}", exc_info=True)
        # Resetar providers em caso de falha para evitar estado inconsistente
        _tracer_provider = None
        trace.set_tracer_provider(trace.NoOpTracerProvider()) # Define NoOp para evitar erros futuros

def get_tracer(name: str) -> trace.Tracer:
    """
    Obtém uma instância do Tracer configurado.

    Args:
        name: Nome do módulo ou componente que está criando o span.

    Returns:
        Instância do Tracer OpenTelemetry.
    """
    if not _tracer_provider:
        # Se não inicializado, retorna um NoOpTracer para evitar erros
        # Idealmente, initialize_telemetry deve ser chamado no ponto de entrada
        logger.warning("Telemetria não inicializada, retornando NoOpTracer.")
        return trace.get_tracer(name, tracer_provider=trace.NoOpTracerProvider())
    return trace.get_tracer(name)
