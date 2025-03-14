import os
import dotenv
import uvicorn
import psycopg2
from psycopg2.extras import DictCursor, Json

from langchain_huggingface import HuggingFaceEmbeddings
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import io
import PyPDF2
from langchain_text_splitters import RecursiveCharacterTextSplitter
from assets import chat_prompty
from services import getChunks
from services.callLLM import call_llm
from utils.createJSON import create_json_from_db
from db import db

dotenv.load_dotenv()

class Item(BaseModel):
    query: str

# Configuração do modelo de embeddings
model_name = "intfloat/multilingual-e5-large-instruct"
model_kwargs = {"device": "cpu"}
encode_kwargs = {"normalize_embeddings": True}
hf = HuggingFaceEmbeddings(model_name=model_name, model_kwargs=model_kwargs, encode_kwargs=encode_kwargs)

app = FastAPI()

# Configuração do CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

@app.get("/")
async def root():
    return {"message": "API de Valoração de Tecnologias com PostgreSQL"}

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Faz upload de um documento PDF, armazena no banco de dados e processa para indexação.
    """
    try:
        # Validar tipo de arquivo
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Apenas arquivos PDF são suportados no momento.")
        
        # Ler conteúdo do arquivo
        file_content = await file.read()
        
        # Processar PDF para extração de texto
        pdf_file = io.BytesIO(file_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        conteudo_texto = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                conteudo_texto += page_text + "\n\n"
        
        # Dividir em chunks
        chunks = getChunks.getChunksNLTK(conteudo_texto)
        
        # Estabelecer conexão com o banco de dados
        conn = db.get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        # Inserir documento original
        cursor.execute(
            """
            INSERT INTO documentos_originais (nome_arquivo, tipo_arquivo, conteudo_binario, metadados)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (file.filename, "pdf", psycopg2.Binary(file_content), Json({"origem": "upload"}))
        )
        
        documento_id = cursor.fetchone()['id']
        
        # Processar chunks e inserir
        for i, chunk in enumerate(chunks):
            # Calcular embedding
            embedding = hf.embed_query(chunk)
            
            # Definir metadados
            metadados = {
                "filename": file.filename,
                "chunk_id": i
            }
            
            # Inserir no banco de dados
            cursor.execute(
                """
                INSERT INTO chunks_vetorizados 
                (documento_id, texto, embedding, pagina, posicao, metadados)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    documento_id, 
                    chunk, 
                    embedding, 
                    1,  # Página (simplificado)
                    i,  # Posição 
                    Json(metadados)
                )
            )
        
        # Fechar conexão
        cursor.close()
        conn.close()
        
        return {
            "status": "success",
            "documento_id": documento_id,
            "chunks_processados": len(chunks),
            "nome_arquivo": file.filename
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar documento: {str(e)}")

@app.post("/chat")
async def chat(item: Item):
    """
    Processa uma consulta do usuário usando RAG com o banco de dados vetorial.
    """
    query = item.query

    try:
        # Calcular embedding da consulta
        query_embedding = hf.embed_query(query)

        # Buscar documentos similares
        search_result = db.search_similar_documents(query_embedding)
       
        # Cria um arquivo JSON com os dados encontrados
        create_json_from_db(search_result)
                
        # Preparar contexto para o LLM
        context = ""
        list_result = []
        mapping = {}
        
        for i, result in enumerate(search_result):
            context += f"Contexto {i}\n{result['texto']}\n\n"
            path = result['metadados'].get('path', '') if result['metadados'] else ''
            mapping[f"Contexto {i}"] = path
            list_result.append({
                "id": i, 
                "path": path, 
                "content": result['texto']
            })
        
        # Preparar mensagens para o LLM
        messages = [chat_prompty.rolemsg, {"role": "user", "content": f"Documents:\n{context}\n\nQuestion: {query}"}]
        
        response = call_llm(messages)
        
        return {"response": response}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar consulta: {str(e)}")

@app.get("/documentos")
async def listar_documentos():
    """
    Lista todos os documentos armazenados no banco de dados.
    """
    try:
        documentos = listar_documentos()
        
        # Converter para formato JSON
        resultado = []
        for doc in documentos:
            resultado.append({
                "id": doc["id"],
                "nome": doc["nome_arquivo"],
                "tipo": doc["tipo_arquivo"],
                "data_upload": doc["data_upload"].isoformat(),
                "metadados": doc["metadados"],
                "total_chunks": doc["chunks_count"]
            })
        
        return resultado
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar documentos: {str(e)}")

@app.delete("/truncate/{nome_tabela}")
def limpar_tabela_endpoint(nome_tabela: str):
    return db.limpar_tabela(nome_tabela)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8001")))