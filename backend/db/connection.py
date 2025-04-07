"""
Gerenciamento de conexões com o banco de dados PostgreSQL.
"""

import os
import psycopg2
from psycopg2.extras import DictCursor
from contextvars import ContextVar
from typing import Optional, Dict, Any
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)

# Obter as configurações
settings = get_settings()

# URL de conexão com o banco de dados
DATABASE_URL = settings.DATABASE_URL

# ContextVar para armazenar conexões dentro de contextos assíncronos
connection_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "connection_context", default=None
)


def get_connection():
    """
    Retorna uma conexão com o banco de dados.
    Conexões são reutilizadas dentro do mesmo contexto.

    Returns:
        psycopg2.connection: Conexão com o banco de dados
    """
    # Verificar se já existe uma conexão no contexto atual
    context = connection_context.get()

    if context is not None and "connection" in context:
        conn = context["connection"]
        # Verificar se a conexão ainda está ativa
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return conn
        except Exception as e:
            logger.warning(f"Conexão inativa, criando nova: {e}")
            # Conexão inativa, continuar para criar uma nova

    # Criar nova conexão
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True

        # Armazenar no contexto
        connection_context.set({"connection": conn})

        return conn
    except Exception as e:
        logger.error(f"Erro ao conectar ao banco de dados: {e}")
        raise


def get_cursor(dict_cursor=True):
    """
    Retorna um cursor para executar operações no banco de dados.

    Args:
        dict_cursor (bool): Se True, retorna um DictCursor (resultados como dicionários)
                           Se False, retorna um cursor padrão (resultados como tuplas)

    Returns:
        psycopg2.cursor: Cursor para o banco de dados
    """
    conn = get_connection()

    if dict_cursor:
        return conn.cursor(cursor_factory=DictCursor)
    else:
        return conn.cursor()


def close_connection():
    """
    Fecha a conexão com o banco de dados se existir no contexto atual.
    """
    context = connection_context.get()

    if context is not None and "connection" in context:
        conn = context["connection"]
        try:
            conn.close()
            logger.debug("Conexão com o banco de dados fechada")
        except Exception as e:
            logger.warning(f"Erro ao fechar conexão: {e}")

        # Remover do contexto
        connection_context.set(None)


def execute_query(query, params=None, fetch=True, dict_cursor=True):
    """
    Executa uma consulta SQL e opcionalmente retorna os resultados.

    Args:
        query (str): Consulta SQL a ser executada
        params (tuple|dict): Parâmetros para a consulta
        fetch (bool): Se True, retorna os resultados da consulta
        dict_cursor (bool): Se True, retorna resultados como dicionários

    Returns:
        list: Resultados da consulta, se fetch=True
        None: Se fetch=False
    """
    cursor = get_cursor(dict_cursor)

    try:
        cursor.execute(query, params)

        if fetch:
            return cursor.fetchall()
        return None
    except Exception as e:
        logger.error(f"Erro ao executar query: {e}")
        raise
    finally:
        cursor.close()


def execute_query_single_result(query, params=None, dict_cursor=True):
    """
    Executa uma consulta SQL e retorna somente o primeiro resultado.

    Args:
        query (str): Consulta SQL a ser executada
        params (tuple|dict): Parâmetros para a consulta
        dict_cursor (bool): Se True, retorna resultado como dicionário

    Returns:
        dict|tuple: Primeiro resultado da consulta, ou None se não houver resultados
    """
    cursor = get_cursor(dict_cursor)

    try:
        cursor.execute(query, params)
        return cursor.fetchone()
    except Exception as e:
        logger.error(f"Erro ao executar query para resultado único: {e}")
        raise
    finally:
        cursor.close()


def execute_transaction(queries_and_params):
    """
    Executa múltiplas operações em uma única transação.

    Args:
        queries_and_params (list): Lista de tuplas (query, params)

    Returns:
        bool: True se a transação foi concluída com sucesso
    """
    conn = get_connection()

    # Garantir que autocommit está desativado para a transação
    original_autocommit = conn.autocommit
    conn.autocommit = False

    cursor = conn.cursor()

    try:
        for query, params in queries_and_params:
            cursor.execute(query, params)

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro na transação, rollback realizado: {e}")
        raise
    finally:
        cursor.close()
        # Restaurar configuração original
        conn.autocommit = original_autocommit
