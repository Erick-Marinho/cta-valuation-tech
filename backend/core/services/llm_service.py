"""
Serviço para interação com modelos de linguagem.
"""
import os
import logging
import time
from typing import Dict, Any, List, Optional
from openai import OpenAI
from core.factory.model_client_factory import ModelClientFactory
from core.config import get_settings
from core.exceptions import LLMServiceError
from utils.logging import track_timing
from core.metrics import (
    LLM_REQUEST_COUNTER,
    LLM_REQUEST_LATENCY,
    LLM_TOKEN_COUNTER,
    MetricsTimer
)

from langsmith.wrappers import wrap_openai
from langsmith import traceable

logger = logging.getLogger(__name__)

class LLMService:
    """
    Serviço para geração de texto com modelos de linguagem.
    
    Responsabilidades:
    - Integração com APIs de LLM 
    - Gestão de prompts e contextos
    - Tratamento de erros e fallbacks
    - Métricas e logging
    """
    
    def __init__(self):
        """
        Inicializa o serviço de LLM.
        """
        self.settings = get_settings()
        self._initialize_client()
        # self.client = ModelClientFactory._initialize_client("nvidia", self.settings)
        self._metrics = {
            "requests_total": 0,
            "tokens_input_total": 0,
            "tokens_output_total": 0,
            "errors_total": 0,
            "avg_response_time": 0
        }
    
    def _initialize_client(self):
        """
        Inicializa o cliente para a API de LLM.
        """
        try:
            # Cliente para a API da NVIDIA
            self.client = wrap_openai(OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=self.settings.API_KEY_NVIDEA
            ))
            logger.info("Cliente LLM inicializado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao inicializar cliente LLM: {e}")
            raise LLMServiceError(f"Erro ao inicializar cliente LLM: {e}")
    
    @track_timing
    @traceable # Auto-trace this function with Langsmith
    async def generate_text(self, system_prompt: str, user_prompt: str, 
                          model: str = None, max_tokens: int = 1024, 
                          temperature: float = 0.3) -> str:
        """
        Gera texto usando o modelo de linguagem.
        
        Args:
            system_prompt: Prompt do sistema (instruções)
            user_prompt: Prompt do usuário (consulta)
            model: Nome do modelo (opcional)
            max_tokens: Número máximo de tokens na resposta
            temperature: Temperatura para geração (0.0 - 1.0)
            
        Returns:
            str: Texto gerado
        """
        if not model:
            model = "meta/llama3-70b-instruct"  # Modelo padrão
        
        try:
            # Estimar tokens de entrada (aproximação simples)
            input_tokens = len(system_prompt.split()) + len(user_prompt.split())
            LLM_TOKEN_COUNTER.labels(type="input").inc(input_tokens)
            
            # Preparar mensagens
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Chamar a API
            with MetricsTimer(LLM_REQUEST_LATENCY):
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=0.9,
                    frequency_penalty=0.3,
                    presence_penalty=0.2,
                    stream=False
                )
            
            # Extrair resposta
            result = response.choices[0].message.content
            
            # Estimar tokens de saída (aproximação simples)
            output_tokens = len(result.split())
            LLM_TOKEN_COUNTER.labels(type="output").inc(output_tokens)
            
            # Registrar sucesso
            LLM_REQUEST_COUNTER.labels(status="success", model=model).inc()
            
            logger.info(f"Geração de texto concluída, {output_tokens} tokens gerados")
            
            return result
            
        except Exception as e:
            # Registrar erro
            LLM_REQUEST_COUNTER.labels(status="error", model=model).inc()
            logger.error(f"Erro ao gerar texto com LLM: {e}")
            raise LLMServiceError(f"Erro ao gerar texto: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Retorna métricas de uso do serviço.
        
        Returns:
            dict: Métricas de uso
        """
        return {
            **self._metrics,
            "avg_tokens_per_request": (
                self._metrics["tokens_output_total"] / max(1, self._metrics["requests_total"])
            ),
            "error_rate": (
                self._metrics["errors_total"] / max(1, self._metrics["requests_total"])
            )
        }

# Instância singleton
_llm_service_instance: Optional[LLMService] = None

def get_llm_service() -> LLMService:
    """
    Retorna a instância do serviço de LLM.
    
    Returns:
        LLMService: Instância do serviço
    """
    global _llm_service_instance
    
    if _llm_service_instance is None:
        _llm_service_instance = LLMService()
    
    return _llm_service_instance