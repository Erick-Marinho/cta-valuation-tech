import json
import os
from datetime import datetime

def create_json_from_db(data):
  dados_json = [
      {
        'id': item[0],
        'texto': item[1],
        'metadados': item[2],
        'pontuacao': item[3]
      }
      for item in data
  ]

  nome_arquivo = 'dados.json'

  with open(nome_arquivo, 'w', encoding='utf-8') as arquivo:
      json.dump(dados_json, arquivo, ensure_ascii=False, indent=4)


def create_json_from_chunks(dados, nome_arquivo, pasta_base="chunks_outputs"):
    """
    Cria um arquivo JSON com os chunks em uma pasta específica.
    
    Args:
        dados: Lista de chunks para salvar
        pasta_base: Nome da pasta onde os arquivos JSON serão salvos
    """
    # Criar a pasta se não existir
    if not os.path.exists(pasta_base):
        os.makedirs(pasta_base)
    
    # Gerar nome do arquivo com timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"{nome_arquivo}_{timestamp}.json"
    caminho_completo = os.path.join(pasta_base, nome_arquivo)

    try:
        if not isinstance(dados, list):
            raise ValueError("Os dados fornecidos não são uma lista.")

        # Criar um dicionário numerado
        dados_formatados = [{str(i + 1): chunk.replace("\n", " ")} for i, chunk in enumerate(dados)]

        with open(caminho_completo, "w", encoding="utf-8") as arquivo:
            json.dump(dados_formatados, arquivo, ensure_ascii=False, indent=4)
        
        print(f"Arquivo JSON criado com sucesso em: {caminho_completo}")

    except Exception as e:
        print(f"Erro ao salvar o arquivo JSON: {e}")
