from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class LLMProvider(ABC):
    """
    Interface abstrata para provedores de Large Language Models (LLMs).

    Define o contrato que as implementações concretas (OpenAI, HuggingFace, etc.)
    devem seguir para gerar respostas baseadas em prompts e contexto.
    """

    @abstractmethod
    async def generate_response(
        self,
        prompt: str,
        context: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        # Adicionar outros parâmetros relevantes conforme necessário (stop_sequences, etc.)
    ) -> str:
        """
        Gera uma resposta textual usando o LLM.

        Args:
            prompt: A instrução ou pergunta principal para o LLM.
            context: Informações contextuais recuperadas (ex: chunks relevantes)
                     para embasar a resposta.
            history: Histórico da conversa (lista de dicionários {'role': 'user'/'assistant', 'content': ...})
                     para manter a continuidade.
            max_tokens: Número máximo de tokens a serem gerados na resposta.
            temperature: Controla a aleatoriedade da resposta (valores mais altos = mais criativo).

        Returns:
            A resposta gerada pelo LLM como uma string.

        Raises:
            Exception: Em caso de erro na comunicação com a API do LLM ou falha na geração.
        """
        pass

    # Opcional: Adicionar outros métodos se necessário, como validação de modelos, etc.
    # @abstractmethod
    # async def list_available_models(self) -> List[str]:
    #     pass
