"""
Utilitários para validação de dados.
"""
import re
import logging
from typing import List, Optional, Union, Dict, Any

logger = logging.getLogger(__name__)

def validate_text(text: str, min_length: int = 1, max_length: Optional[int] = None) -> bool:
    """
    Valida se o texto está dentro dos limites especificados.
    
    Args:
        text: Texto a ser validado
        min_length: Comprimento mínimo (padrão: 1)
        max_length: Comprimento máximo (opcional)
        
    Returns:
        bool: True se o texto é válido, False caso contrário
    """
    if not isinstance(text, str):
        logger.warning(f"Texto não é uma string: {type(text)}")
        return False
        
    text_len = len(text)
    
    if text_len < min_length:
        logger.debug(f"Texto muito curto: {text_len} < {min_length}")
        return False
        
    if max_length is not None and text_len > max_length:
        logger.debug(f"Texto muito longo: {text_len} > {max_length}")
        return False
        
    return True

def validate_file_type(filename: str, allowed_types: List[str]) -> bool:
    """
    Valida se o tipo de arquivo é permitido.
    
    Args:
        filename: Nome do arquivo
        allowed_types: Lista de extensões permitidas (sem o ponto)
        
    Returns:
        bool: True se o tipo é permitido, False caso contrário
    """
    if not filename or not isinstance(filename, str):
        logger.warning(f"Nome de arquivo inválido: {filename}")
        return False
        
    # Extrair extensão
    parts = filename.split('.')
    if len(parts) < 2:
        logger.warning(f"Arquivo sem extensão: {filename}")
        return False
        
    extension = parts[-1].lower()
    
    if extension not in allowed_types:
        logger.warning(f"Tipo de arquivo não permitido: {extension}. Permitidos: {allowed_types}")
        return False
        
    return True

def validate_query(query: str) -> Union[bool, Dict[str, Any]]:
    """
    Valida uma consulta do usuário.
    
    Args:
        query: Texto da consulta
        
    Returns:
        bool | dict: True se válida, ou dicionário com erros
    """
    errors = {}
    
    # Verificar comprimento mínimo significativo
    if not query or len(query.strip()) < 3:
        errors["length"] = "A consulta deve ter pelo menos 3 caracteres"
    
    # Verificar se não é apenas números ou caracteres especiais
    if query and not re.search(r'[a-zA-Z]', query):
        errors["content"] = "A consulta deve conter pelo menos uma letra"
    
    # Verificar comprimento máximo razoável
    if len(query) > 500:
        errors["length"] = "A consulta é muito longa (máximo 500 caracteres)"
    
    if errors:
        return errors
        
    return True