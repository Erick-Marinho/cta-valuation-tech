# utils/telemetry.py
"""
Configuração e utilidades para o OpenTelemetry.

Este módulo configura o rastreamento distribuído usando OpenTelemetry,
permitindo acompanhar o fluxo de requisições através dos componentes do sistema.
"""
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

import logging

logger = logging.getLogger(__name__)

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
    try:
        # Criar recurso identificando o serviço
        resource = Resource(attributes={
            SERVICE_NAME: service_name
        })
        
        # Configurar provedor de tracer com o recurso
        provider = TracerProvider(resource=resource)
        
        # Criar exportador para o coletor OpenTelemetry (Grafana Tempo)
        otlp_exporter = OTLPSpanExporter(endpoint="tempo:4317", insecure=True)
        
        # Criar processador para exportar spans em batch
        span_processor = BatchSpanProcessor(otlp_exporter)
        
        # Adicionar processador ao provedor
        provider.add_span_processor(span_processor)
        
        # Definir provedor global
        trace.set_tracer_provider(provider)
        
        logger.info(f"OpenTelemetry configurado com sucesso para o serviço '{service_name}'")
        
        # Retornar um tracer para uso na aplicação
        return trace.get_tracer(__name__)
        
    except Exception as e:
        logger.error(f"Erro ao configurar OpenTelemetry: {str(e)}")
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
