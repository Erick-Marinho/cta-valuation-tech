import os
import PyPDF2
import dotenv
from os import listdir
from os.path import isfile, join, isdir
import psycopg2
from psycopg2.extras import Json, DictCursor
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings

dotenv.load_dotenv()

# Configuração do modelo de embeddings
model_name = "intfloat/multilingual-e5-large-instruct"
model_kwargs = {"device": "cuda"}
encode_kwargs = {"normalize_embeddings": True}
hf = HuggingFaceEmbeddings(model_name=model_name, model_kwargs=model_kwargs, encode_kwargs=encode_kwargs)

# Conexão com o PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/vectordb")

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
        embedding vector(768),
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

def lista_arquivos(dir):
    """Listar todos os arquivos em um diretório e seus subdiretórios."""
    arquivos_list = []

    for item in listdir(dir):
        if isfile(join(dir, item)):
            arquivos_list.append(join(dir, item))
        elif isdir(join(dir, item)):
            arquivos_list += lista_arquivos(join(dir, item))
    return arquivos_list
  
def limpar_texto(texto):
    """Limpa o texto para evitar problemas com caracteres especiais."""
    if texto is None:
        return ""
    texto_limpo = texto.replace("\x00", "")
    return texto_limpo

def processar_arquivo(arquivo_path):
    """Processa um arquivo PDF e retorna seu conteúdo binário e chunks de texto."""
    try:
        # Ler o arquivo binário
        with open(arquivo_path, 'rb') as file:
            conteudo_binario = file.read()
        
        # Extrair texto do PDF
        conteudo_texto = ""
        if arquivo_path.endswith(".pdf"):
            read = PyPDF2.PdfReader(arquivo_path)
            for page in read.pages:
                texto_pagina = page.extract_text()
                if texto_pagina:
                    texto_pagina = limpar_texto(texto_pagina)
                    conteudo_texto += " " + texto_pagina
        
        # Se não tiver conteúdo, retornar vazio
        if not conteudo_texto.strip():
            return conteudo_binario, [], []
        
        # Dividir texto em chunks
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        chunks = splitter.split_text(conteudo_texto)
        
        # Gerar embeddings para cada chunk
        embeddings = []
        for chunk in chunks:
            embedding = hf.embed_query(chunk)
            embeddings.append(embedding)
        
        return conteudo_binario, chunks, embeddings
    
    except Exception as e:
        print(f"Erro ao processar arquivo {arquivo_path}: {e}")
        return None, [], []

def migrar_documentos(dir_documentos="documents"):
    """Migra documentos da pasta para o PostgreSQL."""
    criar_tabelas()
    
    # Obter lista de arquivos
    arquivos = lista_arquivos(dir_documentos)
    print(f"Encontrados {len(arquivos)} arquivos em {dir_documentos}")
    
    if not arquivos:
        print("Nenhum arquivo encontrado para migração")
        return
    
    conn = conectar_bd()
    
    for arquivo in arquivos:
        try:
            nome_arquivo = os.path.basename(arquivo)
            tipo_arquivo = os.path.splitext(arquivo)[1][1:].lower()  # Obtém a extensão sem o ponto
            
            print(f"Processando: {nome_arquivo}")
            
            # Extrair conteúdo e processar
            conteudo_binario, chunks, embeddings = processar_arquivo(arquivo)
            if not conteudo_binario:
                print(f"Pulando arquivo {nome_arquivo}: erro na extração")
                continue
            
            # Inserir documento original
            cursor = conn.cursor(cursor_factory=DictCursor)
            cursor.execute(
                """
                INSERT INTO documentos_originais (nome_arquivo, tipo_arquivo, conteudo_binario, metadados)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (nome_arquivo, tipo_arquivo, psycopg2.Binary(conteudo_binario), Json({"path": arquivo}))
            )
            
            documento_id = cursor.fetchone()['id']
            
            # Inserir chunks
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk = limpar_texto(chunk)
                
                metadados = {
                    "path": arquivo,
                    "chunk_id": i
                }
                
                cursor.execute(
                    """
                    INSERT INTO chunks_vetorizados 
                    (documento_id, texto, embedding, pagina, posicao, metadados)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (documento_id, chunk, embedding, 1, i, Json(metadados))
                )
            
            print(f"Documento {nome_arquivo} migrado com {len(chunks)} chunks")
            
        except Exception as e:
            print(f"Erro ao migrar documento {arquivo}: {e}")
    
    conn.close()
    print("Migração concluída!")

if __name__ == "__main__":
    migrar_documentos()