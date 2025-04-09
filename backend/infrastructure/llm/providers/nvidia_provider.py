import os
import logging
import time
import tiktoken
import asyncio
from typing import Dict, Any, List, Optional

# Importações da nova estrutura
from application.interfaces.llm_provider import LLMProvider
from config.config import get_settings
from shared.exceptions import LLMServiceError # Manter ou criar uma exceção específica da infra
from utils.logging import track_timing # Manter se usado
from utils.telemetry import get_tracer
from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode
from utils.metrics_prometheus import record_llm_time, record_tokens, record_llm_error

# Usar cliente OpenAI para API NVIDIA
from openai import OpenAI, AsyncOpenAI # AsyncOpenAI pode ser usado diretamente se suportado pela API NVIDIA

logger = logging.getLogger(__name__)

class NvidiaProvider(LLMProvider):
    """
    Implementação do LLMProvider para interagir com a API da NVIDIA
    usando a interface compatível com OpenAI.
    """

    def __init__(self):
        """
        Inicializa o provedor NVIDIA LLM.
        """
        self.settings = get_settings()
        with get_tracer(__name__).start_as_current_span(
            "nvidia_provider.__init__"
        ) as init_span:
            self.tracer = get_tracer(__name__)
            init_span.set_attribute("llm.provider", "nvidia")

            # Inicializar o tokenizador Tiktoken
            try:
                self.tokenizer = tiktoken.get_encoding("cl100k_base")
                init_span.set_attribute("tokenizer.encoding", "cl100k_base")
            except Exception as e:
                logger.warning(f"Tiktoken cl100k_base não encontrado. Usando split(). Erro: {e}")
                init_span.set_attribute("tokenizer.encoding", "fallback_split")
                init_span.record_exception(e)
                self.tokenizer = None # Define como None para usar fallback

            self._initialize_client()

    def _initialize_client(self):
        """
        Inicializa o cliente OpenAI para a API NVIDIA.
        """
        with self.tracer.start_as_current_span(
            "nvidia_provider.initialize_client", kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Nota: Verificar se a API NVIDIA suporta AsyncOpenAI seria ideal.
                # Por enquanto, mantemos OpenAI síncrono e usaremos to_thread.
                self.client = OpenAI(
                    base_url="https://integrate.api.nvidia.com/v1",
                    api_key=self.settings.API_KEY_NVIDEA,
                )
                span.set_attribute("rpc.system", "openai_compatible")
                span.set_attribute("server.address", "integrate.api.nvidia.com")
                span.set_attribute("llm.client.initialized", True)
                span.set_status(Status(StatusCode.OK))
                logger.info("Cliente LLM (NVIDIA Provider) inicializado com sucesso")
            except Exception as e:
                span.set_attribute("llm.client.initialized", False)
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, description=str(e)))
                logger.error(f"Erro ao inicializar cliente LLM (NVIDIA Provider): {e}", exc_info=True)
                # Considerar relançar uma exceção mais específica da infraestrutura
                raise LLMServiceError(f"Erro ao inicializar cliente LLM (NVIDIA Provider): {e}") from e

    def _count_tokens(self, text: str) -> int:
        """
        Conta tokens usando Tiktoken ou fallback.
        """
        if not text:
            return 0
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except Exception as e:
                logger.warning(f"Erro tiktoken: {e}. Usando split().")
                # Fallback: Contagem baseada em palavras como aproximação
                return len(text.split())
        else:
            # Fallback: Contagem baseada em palavras
            return len(text.split())

    def _build_messages(
        self,
        prompt: str,
        context: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """ Constrói a lista de mensagens para a API. """
        messages = []

        # 1. System Prompt (Instrução Geral + Contexto se houver)
        system_content = "Você é um assistente prestativo." # Prompt base
        if context:
            # Adiciona contexto ao prompt do sistema ou como mensagem separada
            # Escolha: Adicionar ao prompt do sistema parece razoável aqui.
            system_content += "\n\nUse o seguinte CONTEXTO para responder à pergunta do usuário:\n---\n"
            system_content += context
            system_content += "\n---"
        messages.append({"role": "system", "content": system_content})

        # 2. Histórico (se houver)
        if history:
            for message in history:
                # Validar 'role' e 'content' seria bom aqui
                if message.get("role") in ["user", "assistant"] and message.get("content"):
                    messages.append({"role": message["role"], "content": message["content"]})

        # 3. Prompt Atual do Usuário
        messages.append({"role": "user", "content": prompt})

        return messages

    async def generate_response(
        self,
        prompt: str,
        context: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Gera uma resposta textual usando o LLM da NVIDIA via API compatível OpenAI.

        Implementa a interface LLMProvider.
        """
        with self.tracer.start_as_current_span(
            "nvidia_provider.generate_response", kind=SpanKind.CLIENT
        ) as span:
            start_time = time.time()

            # Definir padrões ou obter de settings
            effective_model = self.settings.LLM_MODEL or "meta/llama3-70b-instruct"
            effective_max_tokens = max_tokens or 1024
            effective_temperature = temperature if temperature is not None else 0.3

            span.set_attribute("llm.request.model", effective_model)
            span.set_attribute("llm.request.max_tokens", effective_max_tokens)
            span.set_attribute("llm.request.temperature", effective_temperature)
            span.set_attribute("llm.provider", "nvidia")

            try:
                # Construir lista de mensagens
                messages = self._build_messages(prompt, context, history)

                # Calcular tokens de entrada (aproximado se usar fallback)
                input_tokens = sum(self._count_tokens(msg["content"]) for msg in messages)
                token_count_method = "tiktoken" if self.tokenizer else "split"
                span.set_attribute("llm.usage.prompt_tokens", input_tokens)
                span.set_attribute("llm.token_count_method", token_count_method)
                record_tokens(input_tokens, "input") # Métrica

                # --- Chamada Assíncrona à API Síncrona ---
                def sync_llm_call():
                    return self.client.chat.completions.create(
                        model=effective_model,
                        messages=messages,
                        max_tokens=effective_max_tokens,
                        temperature=effective_temperature,
                        # Outros parâmetros podem ser adicionados/configurados
                        # top_p=0.9,
                        # frequency_penalty=0.3,
                        # presence_penalty=0.2,
                        stream=False, # Manter False para esta implementação
                    )

                response = await asyncio.to_thread(sync_llm_call)
                # -----------------------------------------

                response_text = response.choices[0].message.content if response.choices else ""
                finish_reason = response.choices[0].finish_reason if response.choices else "unknown"
                response_model_name = response.model # Modelo retornado pela API

                output_tokens = self._count_tokens(response_text)

                # Telemetria e Métricas
                span.set_attribute("llm.usage.completion_tokens", output_tokens)
                span.set_attribute("llm.usage.total_tokens", input_tokens + output_tokens)
                span.set_attribute("llm.response.model", response_model_name or effective_model)
                span.set_attribute("llm.response.finish_reason", finish_reason)
                span.set_attribute("llm.response.length", len(response_text))
                record_tokens(output_tokens, "output")

                elapsed_time = time.time() - start_time
                record_llm_time(elapsed_time, effective_model) # Métrica
                span.set_attribute("duration_ms", int(elapsed_time * 1000))

                logger.info(
                    f"NVIDIA LLM call success ({effective_model}) took {elapsed_time:.2f}s. "
                    f"Tokens In: {input_tokens}, Out: {output_tokens} ({token_count_method}). Finish: {finish_reason}"
                )

                span.set_status(Status(StatusCode.OK))
                return response_text

            except Exception as e:
                elapsed_time = time.time() - start_time
                record_llm_time(elapsed_time, effective_model) # Métrica
                record_llm_error(effective_model) # Métrica

                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, description=str(e)))
                span.set_attribute("error.type", type(e).__name__)

                logger.error(
                    f"Erro na chamada LLM (NVIDIA Provider - {effective_model}): {e}", exc_info=True
                )
                # Considerar relançar uma exceção mais específica da infraestrutura
                raise LLMServiceError(
                    f"Erro ao gerar texto com modelo {effective_model} (NVIDIA Provider): {e}"
                ) from e
