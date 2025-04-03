"""
Serviço para interação com modelos de linguagem.
"""
import os
import logging
import time
import tiktoken
from typing import Dict, Any, List, Optional
from openai import OpenAI
from core.config import get_settings
from core.exceptions import LLMServiceError
from utils.logging import track_timing
from utils.telemetry import get_tracer
from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode
from utils.metrics_prometheus import record_llm_time, record_tokens, record_llm_error


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
        with get_tracer(__name__).start_as_current_span("llm_service.__init__") as init_span:
            self.tracer = get_tracer(__name__)
            init_span.set_attribute("llm.provider", "nvidia")

            # Inicializar o tokenizador Tiktoken
            try:
                # Usar cl100k_base como um padrão razoável
                self.tokenizer = tiktoken.get_encoding("cl100k_base")
                init_span.set_attribute("tokenizer.encoding", "cl100k_base")
            except Exception as e:
                logger.warning(f"Encoding cl100k_base não encontrado. Usando split() como fallback. Erro: {e}")
                init_span.set_attribute("tokenizer.encoding", "fallback_split")
                init_span.record_exception(e)
                self.tokenizer = None

            self._initialize_client()
        
    def _initialize_client(self):
        """
        Inicializa o cliente para a API de LLM.
        """
        with self.tracer.start_as_current_span(
            "llm_service.initialize_client",
            kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Cliente para a API da NVIDIA
                self.client = OpenAI(
                    base_url="https://integrate.api.nvidia.com/v1",
                    api_key=self.settings.API_KEY_NVIDEA
                )
                span.set_attribute("rpc.system", "openai")
                span.set_attribute("server.address", "integrate.api.nvidia.com")
                span.set_attribute("llm.client.initialized", True)
                span.set_status(Status(StatusCode.OK))
                logger.info("Cliente LLM inicializado com sucesso")
            except Exception as e:
                span.set_attribute("llm.client.initialized", False)
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, description=str(e)))
                logger.error(f"Erro ao inicializar cliente LLM: {e}", exc_info=True)
                raise LLMServiceError(f"Erro ao inicializar cliente LLM: {e}") from e
            
    def _count_tokens(self, text: str) -> int:
        """
        Conta tokens usando o tokenizador Tiktoken ou fallback para split().
        """
        if not text: return 0
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except Exception as e:
                logger.warning(f"Erro ao usar tiktoken para contar tokens: {e}. Usando split().")
                return len(text.split())
        else:
            return len(text.split())
        
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
        with self.tracer.start_as_current_span(
            "llm_service.generate_text",
            kind=SpanKind.CLIENT
        ) as span:
            start_time = time.time()

            effective_model = model or self.settings.LLM_MODEL or 'meta/llama3-70b-instruct'
            span.set_attribute("llm.request.model", effective_model)
            span.set_attribute("llm.request.max_tokens", max_tokens)
            span.set_attribute("llm.request.temperature", temperature)

            try:
                system_tokens = self._count_tokens(system_prompt)
                user_tokens = self._count_tokens(user_prompt)
                input_tokens = system_tokens + user_tokens
                token_count_method = "tiktoken" if self.tokenizer else "split"

                span.set_attribute("llm.usage.prompt_tokens", input_tokens)
                span.set_attribute("llm.usage.prompt_tokens_system", system_tokens)
                span.set_attribute("llm.usage.prompt_tokens_user", user_tokens)
                span.set_attribute("llm.token_count_method", token_count_method)

                record_tokens(input_tokens, "input")

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]

                response = self.client.chat.completions.create(
                    model=effective_model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=0.9,
                    frequency_penalty=0.3,
                    presence_penalty=0.2,
                    stream=False
                )

                response_text = response.choices[0].message.content if response.choices else ""
                finish_reason = response.choices[0].finish_reason if response.choices else "unknown"
                response_model_name = response.model

                output_tokens = self._count_tokens(response_text)

                span.set_attribute("llm.usage.completion_tokens", output_tokens)
                span.set_attribute("llm.usage.total_tokens", input_tokens + output_tokens)
                span.set_attribute("llm.response.model", response_model_name)
                span.set_attribute("llm.response.finish_reason", finish_reason)
                span.set_attribute("llm.response.length", len(response_text))

                record_tokens(output_tokens, "output")

                elapsed_time = time.time() - start_time
                record_llm_time(elapsed_time, effective_model)
                span.set_attribute("duration_ms", int(elapsed_time * 1000))

                logger.info(
                    f"LLM call success ({effective_model}) took {elapsed_time:.2f}s. "
                    f"Tokens In: {input_tokens}, Out: {output_tokens} ({token_count_method}). Finish: {finish_reason}"
                )

                span.set_status(Status(StatusCode.OK))
                return response_text

            except Exception as e:
                elapsed_time = time.time() - start_time
                record_llm_time(elapsed_time, effective_model)
                record_llm_error(effective_model)

                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, description=str(e)))
                span.set_attribute("error.type", type(e).__name__)

                logger.error(f"Erro na chamada LLM ({effective_model}): {e}", exc_info=True)
                raise LLMServiceError(f"Erro ao gerar texto com modelo {effective_model}: {e}") from e
        

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