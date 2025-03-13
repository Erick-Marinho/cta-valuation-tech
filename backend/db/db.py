import os
import psycopg2

# Conexão com o PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "postgres://admin:-ABnTLnyH_2e~GBOYjI5v3Zgd3b.0~OL@caboose.proxy.rlwy.net:56050/cta-db")

def conectar_bd():
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

