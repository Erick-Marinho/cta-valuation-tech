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
        self.tracer = get_tracer(__name__)
        self._initialize_client()
        
        # Inicializar o tokenizador Tiktoken
        try:
            # cl100k_base é usado por GPT-4, GPT-3.5. Pode ser adequado para Llama 3,
            # mas idealmente verificar a documentação específica do modelo Nvidia/Meta.
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
            # Alternativa: Tentar pelo nome do modelo se suportado pela API da Nvidia (menos provável)
            # self.tokenizer = tiktoken.encoding_for_model(self.settings.LLM_MODEL) # Usar o modelo das settings
        except ValueError:
            logger.warning("Encoding cl100k_base não encontrado ou modelo não mapeado. Usando split() como fallback para contagem de tokens.")
            self.tokenizer = None # Usaremos split() como fallback
    
    def _initialize_client(self):
        """
        Inicializa o cliente para a API de LLM.
        """
        
        with self.tracer.start_as_current_span("initialize_llm_client") as span:
            try:
                # Cliente para a API da NVIDIA
                self.client = OpenAI(
                    base_url="https://integrate.api.nvidia.com/v1",
                    api_key=self.settings.API_KEY_NVIDEA
                )
                span.set_attribute("initialization.success", True)
                logger.info("Cliente LLM inicializado com sucesso")
            except Exception as e:
                span.set_attribute("initialization.success", False)
                span.set_attribute("error.message", str(e))
                span.record_exception(e)
                
                logger.error(f"Erro ao inicializar cliente LLM: {e}")
                raise LLMServiceError(f"Erro ao inicializar cliente LLM: {e}")
            
    def _count_tokens(self, text: str) -> int:
        """
        Conta tokens usando o tokenizador Tiktoken ou fallback para split().
        """
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except Exception as e:
                logger.warning(f"Erro ao usar tiktoken para contar tokens: {e}. Usando split().")
                # Fallback em caso de erro com tiktoken em texto específico
                return len(text.split())
        else:
            # Fallback se o tokenizador não foi inicializado
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
        if not model:
            # Usar modelo das settings se disponível, senão um default
            model = getattr(self.settings, 'LLM_MODEL', 'meta/llama3-70b-instruct')
        
        start_time = time.time()
        
        # Criar span para rastrear a geração de texto
        with self.tracer.start_as_current_span("llm_generate_text") as span:
            # Registrar parâmetros da requisição como atributos
            span.set_attribute("llm.model", model)
            span.set_attribute("llm.max_tokens", max_tokens)
            span.set_attribute("llm.temperature", temperature)
            span.set_attribute("system_prompt.length", len(system_prompt))
            span.set_attribute("user_prompt.length", len(user_prompt))
            
            # Estimar tokens de entrada (aproximação simples)
            input_tokens = len(system_prompt.split()) + len(user_prompt.split())
            span.set_attribute("input.tokens_estimate", input_tokens)
            
            try:
                # Contagem de tokens de entrada usando tiktoken (ou fallback)
                input_tokens = self._count_tokens(system_prompt + user_prompt)
                span.set_attribute("input.tokens", input_tokens) # Registrar contagem precisa no span
                record_tokens(input_tokens, "input") # Enviar para Prometheus
                
                # Preparar mensagens
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                
                # Criar sub-span para a chamada à API
                with self.tracer.start_as_current_span("llm_api_call") as api_span:
                    api_span.set_attribute("llm.api_endpoint", self.client.base_url)
                
                    # Chamar a API
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
                record_tokens(output_tokens, "output")  # Métrica Prometheus
                
                # Calcular média de tempo de resposta
                elapsed_time = time.time() - start_time
                record_llm_time(elapsed_time, model) # Registrar tempo no Prometheus
                span.set_attribute("response_time", elapsed_time)
                
                # Calcular tempo total
                elapsed_time = time.time() - start_time
                
                # Registrar em métrica Prometheus
                record_llm_time(elapsed_time, model)
                
                token_count_method = "tiktoken" if self.tokenizer else "split"
            
                
                logger.info(f"Geração de texto concluída em {elapsed_time:.2f}s. Tokens In: {input_tokens}, Out: {output_tokens} (método: {token_count_method})")
                
                return result
            
            except Exception as e:                
                # Registrar mesmo em caso de erro
                elapsed_time = time.time() - start_time
                record_llm_time(elapsed_time, model)
                record_llm_error(model)
                
                # Registrar no span
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, f"Erro: {e}"))
                
                logger.error(f"Erro ao gerar texto com LLM: {e}", exc_info=True)
                raise LLMServiceError(f"Erro ao gerar texto: {e}")
        

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