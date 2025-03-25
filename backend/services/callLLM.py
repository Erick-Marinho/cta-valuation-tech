import os
from openai import OpenAI
from typing import List, Dict

# Cliente OpenAI para geração de texto
client_ai = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("api_key_nvidea")
)

def call_llm(
      messages: List[Dict], 
      model: str = "meta/llama3-70b-instruct", 
      max_tokens: int = 1024, 
      temperature: float = 0.2,
      top_p: float = 0.9, 
      frequency_penalty: float = 0.3,
      presence_penalty: float = 0.2
      ) -> str:
  try:
      resposta = client_ai.chat.completions.create(
          model=model,
          messages=messages,
          max_tokens=max_tokens,
          temperature=temperature,
          top_p=top_p,       
          frequency_penalty=frequency_penalty,
          presence_penalty=presence_penalty,
          stream=False
      )
      return resposta.choices[0].message.content
  except Exception as e:
      raise Exception(f"Erro ao chamar o LLM: {str(e)}")