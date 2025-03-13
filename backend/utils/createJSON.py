import json

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


def create_json_from_chunks(dados):
  nome_arquivo="chunks.json"

  try:
      if not isinstance(dados, list):
          raise ValueError("Os dados fornecidos não são uma lista.")

      # Criar um dicionário numerado
      dados_formatados = [{str(i + 1): chunk.replace("\n", " ")} for i, chunk in enumerate(dados)]

      with open(nome_arquivo, "w", encoding="utf-8") as arquivo:
          json.dump(dados_formatados, arquivo, ensure_ascii=False, indent=4)

  except Exception as e:
      print(f"Erro ao salvar o arquivo JSON: {e}")
