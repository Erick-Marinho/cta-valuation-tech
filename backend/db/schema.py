"""
Definições de schema e tabelas do banco de dados.
Inclui funções para criar, atualizar e verificar o esquema.
"""

import logging
from .connection import get_connection, execute_query

logger = logging.getLogger(__name__)

# Definições das tabelas
SCHEMA_DEFINITIONS = {
    "extensions": ["CREATE EXTENSION IF NOT EXISTS vector;"],
    "tables": [
        """
        CREATE TABLE IF NOT EXISTS documentos_originais (
            id SERIAL PRIMARY KEY,
            nome_arquivo TEXT NOT NULL,
            tipo_arquivo TEXT NOT NULL,
            conteudo_binario BYTEA NOT NULL,
            data_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadados JSONB
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS chunks_vetorizados (
            id SERIAL PRIMARY KEY,
            documento_id INTEGER REFERENCES documentos_originais(id) ON DELETE CASCADE,
            texto TEXT NOT NULL,
            embedding vector(1024),
            pagina INTEGER,
            posicao INTEGER,
            metadados JSONB
        );
        """,
    ],
    "indexes": [
        # Índice para busca vetorial
        """
        CREATE INDEX IF NOT EXISTS chunks_embedding_idx 
        ON chunks_vetorizados 
        USING ivfflat (embedding vector_cosine_ops) 
        WITH (lists = 100);
        """,
        # Índice para busca de texto
        """
        CREATE INDEX IF NOT EXISTS chunks_texto_idx 
        ON chunks_vetorizados 
        USING gin(to_tsvector('portuguese', texto));
        """,
    ],
}


def setup_database():
    """
    Configura o banco de dados, criando as tabelas necessárias se não existirem.
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Criar extensões
        for extension_query in SCHEMA_DEFINITIONS["extensions"]:
            cursor.execute(extension_query)

        # Criar tabelas
        for table_query in SCHEMA_DEFINITIONS["tables"]:
            cursor.execute(table_query)

        # Criar índices
        for index_query in SCHEMA_DEFINITIONS["indexes"]:
            cursor.execute(index_query)

        logger.info("Banco de dados configurado com sucesso")
    except Exception as e:
        logger.error(f"Erro ao configurar banco de dados: {e}")
        raise
    finally:
        cursor.close()


def check_database_version():
    """
    Verifica a versão atual do banco de dados e executa migrações se necessário.
    Em uma aplicação mais complexa, isso seria feito por um sistema de migração como Alembic.
    """
    try:
        # Verificar se a tabela de versões existe
        result = execute_query(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'db_version'
            );
            """,
            fetch=True,
        )

        table_exists = result[0][0]

        if not table_exists:
            # Criar tabela de versões
            execute_query(
                """
                CREATE TABLE db_version (
                    id SERIAL PRIMARY KEY,
                    version VARCHAR(50) NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """,
                fetch=False,
            )

            # Inserir versão inicial
            execute_query(
                """
                INSERT INTO db_version (version) VALUES ('1.0.0');
                """,
                fetch=False,
            )

            logger.info("Schema inicial criado com versão 1.0.0")
            return "1.0.0"

        # Obter versão atual
        result = execute_query(
            """
            SELECT version FROM db_version ORDER BY id DESC LIMIT 1;
            """,
            fetch=True,
        )

        current_version = result[0][0]
        logger.info(f"Versão atual do banco de dados: {current_version}")

        # Aqui você poderia implementar lógica para executar migrações
        # dependendo da versão atual do banco de dados

        return current_version

    except Exception as e:
        logger.error(f"Erro ao verificar versão do banco de dados: {e}")
        raise


def is_database_healthy():
    """
    Verifica se o banco de dados está saudável e acessível.

    Returns:
        bool: True se o banco de dados estiver saudável, False caso contrário
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        return True
    except Exception as e:
        logger.error(f"Banco de dados não está saudável: {e}")
        return False
