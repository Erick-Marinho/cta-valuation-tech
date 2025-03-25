from langsmith.wrappers import wrap_openai
from openai import OpenAI

"""
Factory para criação de clientes de diferentes provedores de modelos de IA.
"""

class ModelClientFactory:
    
  @staticmethod
  def _initialize_client(provider_type, settings):      
      if provider_type.lower() == "nvidia":
          
          client = OpenAI(
              base_url="https://integrate.api.nvidia.com/v1",
              api_key=settings.API_KEY_NVIDEA
          )
          return wrap_openai(client)
      
      elif provider_type.lower() == "openai":
          
          client = OpenAI(
              api_key=settings.API_KEY_OPENAI
          )
          return wrap_openai(client)
      
      elif provider_type.lower() == "anthropic":
          return ""  # Implementar cliente para Anthropic
      
      else:
          raise ValueError(f"Provedor não suportado: {provider_type}")