from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.text_splitter import NLTKTextSplitter
import re

from nltk.tokenize import word_tokenize

import nltk

nltk.download('punkt')
nltk.download('punkt_tab')

def getChunksNLTK(conteudo_texto):  
  text_splitter = NLTKTextSplitter(
    chunk_size=800,  # Tamanho máximo do chunk (em caracteres, mas respeitando frases)
    chunk_overlap=100,  # Sobreposição
  )

  conteudo_texto = re.sub(r'(\w+)-\n(\w+)', r'\1\2', conteudo_texto)

  # Dividir o texto
  chunks = text_splitter.split_text(conteudo_texto)

  final_chunks = []
  for chunk in chunks:
      if len(chunk) > 800:
          sub_chunks = re.split(r',\s*', chunk)  # Divide por vírgula
          temp_chunk = ""
          for part in sub_chunks:
              if len(temp_chunk) + len(part) + 1 <= 800:
                  temp_chunk += (", " if temp_chunk else "") + part
              else:
                  final_chunks.append(temp_chunk)
                  temp_chunk = part
          if temp_chunk:
              final_chunks.append(temp_chunk)
      else:
          final_chunks.append(chunk)

  return final_chunks

# Função para dividir o texto em chunks Recur
def getChunks(conteudo_texto):  
  splitter = RecursiveCharacterTextSplitter(
      chunk_size=800,
      chunk_overlap=100,
      # separators=["\n\n", "\n", ". ", " ", ""]
      separators=[
        "\n\n",  # Quebras de parágrafo
        "\n",    # Quebras de linha
        ". ",    # Fim de frase (espaço após o ponto)
        ", ",    # Vírgula seguida de espaço
        " ",     # Espaço simples
        "-",     # Hífen
        ""       # Corte bruto (último recurso)
    ]
  )
  
  chunks = splitter.split_text(conteudo_texto)
  return chunks