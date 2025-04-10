import logging
from typing import Any, List, Optional, Iterator

from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatResult, ChatGeneration

# Importar nossa implementação e interface
from application.interfaces.llm_provider import LLMProvider
from infrastructure.llm.providers.nvidia_provider import NvidiaProvider # Para type hint

# --- Imports para Wrapper DeepEval ---
import asyncio
from deepeval.models.base_model import DeepEvalBaseLLM
# -------------------------------------

logger = logging.getLogger(__name__)

class LangChainNvidiaChat(BaseChatModel):
    """
    Wrapper LangChain para utilizar nosso NvidiaProvider customizado
    como um BaseChatModel.
    """
    provider: LLMProvider # Recebe a instância do nosso provider

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        Método principal que o LangChain chama para gerar uma resposta.
        """
        # 1. Converter mensagens LangChain para o formato esperado pelo nosso provider
        #    (Provavelmente uma string única ou uma lista de dicts simples)
        #    Exemplo: Concatenar ou formatar baseado nos roles
        system_prompt: str = ""
        user_query: str = ""
        history = []

        for msg in messages:
            if isinstance(msg, SystemMessage):
                system_prompt = msg.content
            elif isinstance(msg, HumanMessage):
                user_query = msg.content
            elif isinstance(msg, AIMessage):
                 # Adicionar ao histórico (se o provider suportar)
                 history.append({"role": "assistant", "content": msg.content})
            # Adicionar outros tipos se necessário (FunctionMessage, etc.)

        # Montar o prompt final (ajustar conforme a necessidade do NvidiaProvider)
        # Esta lógica pode precisar ser mais sofisticada dependendo do provider
        full_prompt = f"{system_prompt}\n\nUsuário: {user_query}" # Exemplo simples
        logger.debug(f"LangChainNvidiaChat: Gerando resposta para prompt formatado.")

        try:
            response_content: str = ""
            # Tentar chamar async com asyncio.run se possível
            if hasattr(self.provider, 'generate_response') and asyncio.iscoroutinefunction(self.provider.generate_response):
                 try:
                     loop = asyncio.get_running_loop()
                     raise RuntimeError("Chamada síncrona _generate não suportada em loop asyncio ativo.")
                 except RuntimeError: # No loop running
                     response_content = asyncio.run(self.provider.generate_response(prompt=full_prompt)) # <<< Espera string
            # Fallback para sync
            elif hasattr(self.provider, 'generate_response') and not asyncio.iscoroutinefunction(self.provider.generate_response):
                 response_content = self.provider.generate_response(prompt=full_prompt) # <<< Espera string
            else:
                 raise NotImplementedError("NvidiaProvider não possui método 'generate_response' compatível.")

            if not isinstance(response_content, str):
                 response_content = str(response_content)
            if not response_content:
                 raise ValueError("Provider retornou conteúdo vazio.")

            chat_generation = ChatGeneration(message=AIMessage(content=response_content)) # <<< Usa a string diretamente
            return ChatResult(generations=[chat_generation])

        except Exception as e:
            logger.error(f"Erro ao gerar resposta via LangChainNvidiaChat: {e}", exc_info=True)
            raise

    # Implementar _stream se quiser suporte a streaming
    # def _stream(...) -> Iterator[ChatGenerationChunk]:
    #     ...

    @property
    def _llm_type(self) -> str:
        """ Retorna um nome identificador para o LLM. """
        return "nvidia-chat-via-wrapper"

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None, # Ajustar tipo se necessário
        **kwargs: Any,
    ) -> ChatResult:
        system_prompt: str = ""
        user_query: str = ""
        history = []

        for msg in messages:
            if isinstance(msg, SystemMessage):
                system_prompt = msg.content
            elif isinstance(msg, HumanMessage):
                user_query = msg.content
            elif isinstance(msg, AIMessage):
                 history.append({"role": "assistant", "content": msg.content})

        full_prompt = f"{system_prompt}\n\nUsuário: {user_query}"
        logger.debug(f"LangChainNvidiaChat (_agenerate): Gerando resposta ASYNC para prompt formatado.")
        try:
            # --- ADICIONAR ATRASO AQUI ---
            await asyncio.sleep(1) # Espera 1 segundo
            # ---------------------------

            response_content: str = ""
            # Chamar async diretamente com await
            if hasattr(self.provider, 'generate_response') and asyncio.iscoroutinefunction(self.provider.generate_response):
                response_content = await self.provider.generate_response(prompt=full_prompt) # Espera string
            else:
                 raise NotImplementedError("NvidiaProvider não possui método async 'generate_response' compatível.")

            if not isinstance(response_content, str):
                 response_content = str(response_content)
            if not response_content:
                 raise ValueError("Provider (async) retornou conteúdo vazio.")

            chat_generation = ChatGeneration(message=AIMessage(content=response_content))
            return ChatResult(generations=[chat_generation])

        except Exception as e:
            logger.error(f"Erro ao gerar resposta ASYNC via LangChainNvidiaChat: {e}", exc_info=True)
            raise

# --- Wrapper DeepEval para NvidiaProvider ---
class DeepEvalNvidiaLLM(DeepEvalBaseLLM):
    """
    Wrapper DeepEval para utilizar nosso NvidiaProvider customizado.
    """
    provider: LLMProvider
    model_name: str # Adicionar anotação de tipo

    def __init__(self, provider: LLMProvider):
        self.provider = provider
        # Tentar obter o nome do modelo do provider ou usar default
        # Assumindo que settings está acessível ou passar como argumento
        try:
             from backend.config.config import get_settings
             settings = get_settings()
             self.model_name = settings.LLM_MODEL
        except ImportError:
             self.model_name = getattr(provider, '_model_name', 'nvidia-custom')
        super().__init__() # Chamar init da classe base

    def load_model(self):
        return self.provider

    # --- CORRIGIR a_generate ---
    async def a_generate(self, prompt: str, **kwargs: Any) -> str:
        logger.debug(f"DeepEvalNvidiaLLM: Gerando resposta async para prompt (kwargs: {kwargs}).")
        try:
            # --- ADICIONAR ATRASO ---
            await asyncio.sleep(1) # Espera 1 segundo antes de chamar a API
            # -----------------------

            # Chamar o método ASYNC do provider esperando uma STRING diretamente
            if hasattr(self.provider, 'generate_response') and asyncio.iscoroutinefunction(self.provider.generate_response):
                response_content: str = await self.provider.generate_response(prompt=prompt)
                if not isinstance(response_content, str):
                     logger.error(f"Provider retornou tipo inesperado: {type(response_content)}. Esperado str.")
                     response_content = str(response_content)
                if not response_content:
                    logger.warning(f"DeepEvalNvidiaLLM.a_generate recebeu conteúdo vazio do provider para o prompt: {prompt[:100]}...")
                return response_content
            else:
                 logger.error("NvidiaProvider não possui um método assíncrono compatível (ex: 'generate_response').")
                 raise NotImplementedError("NvidiaProvider não possui um método assíncrono compatível.")

        except Exception as e:
            logger.error(f"Erro em DeepEvalNvidiaLLM.a_generate: {e}", exc_info=True)
            return f"Erro ao gerar resposta: {str(e)}" # Retorna string de erro

    def generate(self, prompt: str) -> str:
        """ Método sync opcional. Tentar implementar de forma mais segura. """
        logger.debug(f"DeepEvalNvidiaLLM: Gerando resposta sync para prompt.")
        try:
            # Tentar rodar o a_generate usando asyncio.run
            try:
                loop = asyncio.get_running_loop()
                logger.error("DeepEvalNvidiaLLM.generate chamada enquanto um loop asyncio já está rodando. Chamada síncrona não suportada neste contexto.")
                raise RuntimeError("Chamada síncrona não suportada em loop asyncio ativo.")
            except RuntimeError: # Nenhum loop rodando, podemos usar asyncio.run
                 logger.debug("Nenhum loop asyncio rodando, usando asyncio.run para chamar a_generate.")
                 return asyncio.run(self.a_generate(prompt=prompt)) # <<< Chama a versão async

        except Exception as e:
            logger.error(f"Erro em DeepEvalNvidiaLLM.generate: {e}", exc_info=True)
            return f"Erro ao gerar resposta: {e}"

    def get_model_name(self) -> str:
        return self.model_name
# --- Fim Wrapper DeepEval ---
