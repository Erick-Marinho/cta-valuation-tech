import os
from os import listdir
from os.path import isfile, join, isdir
import logging
from typing import List # Adicionar Type Hint

logger = logging.getLogger(__name__)

def lista_arquivos(dir_path: str) -> List[str]:
    """Listar todos os arquivos em um diretório e seus subdiretórios."""
    arquivos_list: List[str] = []
    if not isdir(dir_path): # Adicionar verificação se o diretório existe
        logger.error(f"Diretório base não encontrado ou não é um diretório: {dir_path}")
        return arquivos_list
    try:
        for item in listdir(dir_path):
            item_path = join(dir_path, item)
            try: # Adicionar try/except para erros de permissão
                if isfile(item_path):
                    arquivos_list.append(item_path)
                elif isdir(item_path):
                    # Chamada recursiva para subdiretórios
                    arquivos_list.extend(lista_arquivos(item_path)) # Usar extend em vez de +=
            except OSError as e:
                 logger.warning(f"Erro de permissão ou OS ao acessar {item_path}: {e}")
    except FileNotFoundError: # Redundante se já checamos com isdir, mas seguro manter
        logger.error(f"Erro: Diretório não encontrado durante listagem recursiva: {dir_path}")
    except OSError as e:
         logger.error(f"Erro de permissão ou OS ao listar diretório {dir_path}: {e}")

    return arquivos_list
