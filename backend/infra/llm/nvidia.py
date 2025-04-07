"""
Adaptador para LLMs da NVIDIA através da API.
"""

import logging
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class NvidiaLLMAdapter:
    """
    Adaptador para acesso a LLMs da NVIDIA.

    Este adaptador utiliza a API da NVIDIA para gerar texto usando
    modelos como o LLaMa3.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        default_model: str = "meta/llama3-70b-instruct",
    ):
        """
        Inicializa o adaptador para LLMs da NVIDIA.

        Args:
            api_key: Chave de API da NVIDIA
            base_url: URL base da API
            default_model: Modelo padrão a ser utilizado
        """
        self.api_key = api_key
        self.base_url = base_url
        self.default_model = default_model
        self._initialize_client()

        # Métricas de uso
        self._request_count = 0
        self._error_count = 0
        self._token_count = 0
        self._total_latency = 0

    def _initialize_client(self) -> None:
        """
        Inicializa o cliente OpenAI para a API da NVIDIA.
        """
        try:
            logger.info(f"Inicializando cliente LLM para {self.base_url}")

            self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)

            logger.info("Cliente LLM inicializado com sucesso")

        except Exception as e:
            logger.error(f"Erro ao inicializar cliente LLM: {e}")
            raise

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.3,
        top_p: float = 0.9,
        frequency_penalty: float = 0.3,
        presence_penalty: float = 0.2,
    ) -> str:
        """
        Gera texto usando o modelo de linguagem.

        Args:
            system_prompt: Instruções para o sistema
            user_prompt: Prompt do usuário
            model: Modelo a ser utilizado (usa o padrão se não especificado)
            max_tokens: Número máximo de tokens na resposta
            temperature: Controle de aleatoriedade (0-1)
            top_p: Amostragem do nucleus (0-1)
            frequency_penalty: Penalidade para repetição de tokens (0-2)
            presence_penalty: Penalidade para repetição de tópicos (0-2)

        Returns:
            str: Texto gerado
        """
        start_time = time.time()

        try:
            # Incrementar contador de requisições
            self._request_count += 1

            # Determinar o modelo a ser usado
            use_model = model if model else self.default_model

            # Preparar mensagens
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            # Fazer a chamada à API
            response = self.client.chat.completions.create(
                model=use_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                stream=False,
            )

            # Extrair o texto da resposta
            result = response.choices[0].message.content

            # Atualizar métricas
            end_time = time.time()
            latency = end_time - start_time
            self._total_latency += latency

            # Estimar tokens (aproximação simples)
            estimated_tokens = len(result.split())
            self._token_count += estimated_tokens

            logger.info(
                f"Geração de texto concluída em {latency:.2f}s, ~{estimated_tokens} tokens"
            )

            return result

        except Exception as e:
            self._error_count += 1
            logger.error(f"Erro ao gerar texto com LLM: {e}")
            raise

    def get_metrics(self) -> Dict[str, Any]:
        """
        Retorna métricas de uso do adaptador.

        Returns:
            dict: Métricas de uso
        """
        avg_latency = self._total_latency / max(1, self._request_count)
        error_rate = self._error_count / max(1, self._request_count)

        return {
            "request_count": self._request_count,
            "error_count": self._error_count,
            "token_count": self._token_count,
            "error_rate": error_rate,
            "average_latency_seconds": avg_latency,
            "tokens_per_request": self._token_count / max(1, self._request_count),
        }

    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Retorna informações sobre os modelos disponíveis.

        Returns:
            list: Lista de modelos disponíveis
        """
        # Esta é uma lista estática de modelos que sabemos estar disponíveis
        # Em uma implementação real, poderíamos consultar a API para obter essa lista
        return [
            {
                "id": "meta/llama3-70b-instruct",
                "name": "LLaMA 3 70B Instruct",
                "max_tokens": 4096,
                "description": "Modelo LLaMA 3 com 70 bilhões de parâmetros, otimizado para instruções",
            },
            {
                "id": "meta/llama3-8b-instruct",
                "name": "LLaMA 3 8B Instruct",
                "max_tokens": 4096,
                "description": "Modelo LLaMA 3 com 8 bilhões de parâmetros, otimizado para instruções",
            },
            # Adicionar outros modelos conforme necessário
        ]
