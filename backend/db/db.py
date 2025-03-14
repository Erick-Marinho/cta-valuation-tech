import os
import psycopg2
from psycopg2.extras import DictCursor, Json
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException

# Conexão com o PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "postgres://admin:-ABnTLnyH_2e~GBOYjI5v3Zgd3b.0~OL@caboose.proxy.rlwy.net:56050/cta-db")

def get_db_connection():
    """Estabelece conexão com o banco de dados PostgreSQL."""
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    return conn

def criar_tabelas():
    """Cria as tabelas necessárias no PostgreSQL se não existirem."""
    conn = conectar_bd()
    cursor = conn.cursor()
    
    # Criar extensão pgvector
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    
    # Tabela para documentos originais
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documentos_originais (
        id SERIAL PRIMARY KEY,
        nome_arquivo TEXT NOT NULL,
        tipo_arquivo TEXT NOT NULL,
        conteudo_binario BYTEA NOT NULL,
        data_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        metadados JSONB
    );
    """)
    
    # Tabela para chunks vetorizados
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chunks_vetorizados (
        id SERIAL PRIMARY KEY,
        documento_id INTEGER REFERENCES documentos_originais(id) ON DELETE CASCADE,
        texto TEXT NOT NULL,
        embedding vector(1024),
        pagina INTEGER,
        posicao INTEGER,
        metadados JSONB
    );
    """)
    
    # Criar índice para busca vetorial
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS chunks_embedding_idx ON chunks_vetorizados 
    USING ivfflat (embedding vector_cosine_ops);
    """)
    
    cursor.close()
    conn.close()
    print("Tabelas criadas com sucesso!")


def limpar_tabela(nome_tabela):
  try:
      # Conectar ao banco de dados
      conn = conectar_bd()
      cursor = conn.cursor()
      
      # Truncar a tabela (remover todos os registros)
      cursor.execute(f"TRUNCATE TABLE {nome_tabela} RESTART IDENTITY CASCADE;")
      
      # Confirmar a transação
      conn.commit()
      
      print(f"Tabela '{nome_tabela}' foi limpa com sucesso.")

  except Exception as e:
      print(f"Erro ao limpar a tabela: {e}")

  finally:
      # Fechar a conexão
      if cursor:
          cursor.close()
      if conn:
          conn.close()


def search_similar_documents(query_embedding):
    try:
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=DictCursor)

        cursor.execute(
                """
                SELECT 
                    cv.id, 
                    cv.texto, 
                    cv.metadados,
                    1 - (cv.embedding <=> %s::vector) as similarity
                FROM 
                    chunks_vetorizados cv
                ORDER BY 
                    cv.embedding <=> %s::vector
                LIMIT 5
                """,
                (query_embedding, query_embedding)
            )
            
        results = cursor.fetchall()
        cursor.close()
        connection.close()
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar consulta: {str(e)}")
    
def list_documents():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        cursor.execute(
            """
            SELECT 
                id, 
                nome_arquivo, 
                tipo_arquivo, 
                data_upload, 
                metadados,
                (SELECT COUNT(*) FROM chunks_vetorizados WHERE documento_id = documentos_originais.id) as chunks_count
            FROM 
                documentos_originais
            ORDER BY 
                data_upload DESC
            """
        )
        
        documentos = cursor.fetchall()

        cursor.close()
        conn.close()
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar documentos: {str(e)}")