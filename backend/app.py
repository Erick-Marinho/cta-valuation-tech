import os
import dotenv
import uvicorn
import psycopg2
from psycopg2.extras import DictCursor, Json
from openai import OpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import io
import PyPDF2
from langchain_text_splitters import RecursiveCharacterTextSplitter

dotenv.load_dotenv()

class Item(BaseModel):
    query: str

# Configuração do modelo de embeddings
model_name = "intfloat/multilingual-e5-large-instruct"
model_kwargs = {"device": "cpu"}
encode_kwargs = {"normalize_embeddings": True}
hf = HuggingFaceEmbeddings(model_name=model_name, model_kwargs=model_kwargs, encode_kwargs=encode_kwargs)

# Cliente OpenAI para geração de texto
client_ai = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("api_key_nvidea")
)

# Configuração da conexão com o banco de dados
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/vectordb")

# Splitter de texto
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100,
    separators=["\n\n", "\n", ". ", " ", ""]
)

app = FastAPI()

# Configuração do CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

# Função para obter conexão com o banco de dados
def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    return conn

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
        chunks = text_splitter.split_text(conteudo_texto)
        
        # Estabelecer conexão com o banco de dados
        conn = get_db_connection()
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
        
        # Conectar ao banco de dados
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        # Buscar documentos similares
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
        
        search_result = cursor.fetchall()
        
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
        
        # Fechar conexão com o banco de dados
        cursor.close()
        conn.close()
        
        # Prompt do sistema
        rolemsg = {
        "role": "system",
        "content": f"""Você é um assistente especializado em valoração de tecnologias relacionadas ao Patrimônio Genético Nacional e Conhecimentos Tradicionais Associados.

Responda à pergunta do usuário usando APENAS as informações fornecidas nos documentos do contexto. Se a informação não estiver nos documentos, indique claramente que não há dados suficientes sobre o assunto específico nos documentos disponíveis.

IMPORTANTE: Não mencione os "contextos" ou "documentos" na sua resposta. O usuário não sabe que você está consultando diferentes fontes. Apresente a informação de forma natural e fluida.

Para conversas informais ou agradecimentos:
- Se o usuário agradecer, responda com naturalidade: "De nada! Estou à disposição para ajudar com mais informações sobre CTA Value Tech."
- Se o usuário se despedir, responda cordialmente: "Até logo! Se precisar de mais informações sobre valoração de tecnologias e biodiversidade, estarei aqui."
- Para conversas casuais, mantenha o tom amigável e profissional, sem mencionar contextos ou documentos.

Ao responder perguntas técnicas:
1. Analise cuidadosamente todos os documentos fornecidos.
2. Extraia as informações relevantes para a pergunta.
3. Organize a resposta de forma estruturada e coerente.
4. Sintetize as informações como se você já as conhecesse, sem revelar a fonte específica.
5. Forneça uma resposta completa e concisa, evitando repetições.
6. Sempre que aplicável, inclua exemplos práticos detalhados que ilustrem a aplicação dos conceitos abordados.
7. Faça referências diretas e específicas a trechos ou elementos do conteúdo fornecido quando necessário, reforçando o embasamento técnico e a credibilidade da resposta.
8. Se houver desafios ou limitações relevantes, inclua uma breve análise crítica e sugestões para superá-los.

As respostas devem ser em português brasileiro formal, mantendo a terminologia técnica apropriada ao tema de biodiversidade, conhecimentos tradicionais e propriedade intelectual.

Se a pergunta for sobre valores ou cálculos específicos de royalties, detalhe a metodologia utilizada, sem mencionar que está obtendo essa informação de documentos.
"""
        }
        
        # Preparar mensagens para o LLM
        messages = [rolemsg, {"role": "user", "content": f"Documents:\n{context}\n\nQuestion: {query}"}]
        
        # Chamar o LLM
        resposta = client_ai.chat.completions.create(
            model="meta/llama3-70b-instruct",
            messages=messages,
            max_tokens=1024,
            temperature=0.2,
            top_p=0.9,       
            frequency_penalty=0.3,
            presence_penalty=0.2,
            stream=False
        )
        
        response = resposta.choices[0].message.content
        
        return {"response": response}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar consulta: {str(e)}")

@app.get("/documentos")
async def listar_documentos():
    """
    Lista todos os documentos armazenados no banco de dados.
    """
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
        
        cursor.close()
        conn.close()
        
        return resultado
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar documentos: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))