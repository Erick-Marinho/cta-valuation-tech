import os
import dotenv
import uvicorn
from openai import OpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from langchain_qdrant import Qdrant
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CohereRerank
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

dotenv.load_dotenv()

class Item(BaseModel):
    query: str

model_name = "intfloat/multilingual-e5-large-instruct"
model_kwargs = {"device": "cpu"}
encode_kwargs = {"normalize_embeddings": True}

hf = HuggingFaceEmbeddings(model_name=model_name, model_kwargs=model_kwargs, encode_kwargs=encode_kwargs) 

client_ai = OpenAI(base_url="https://integrate.api.nvidia.com/v1",
  api_key=os.getenv("api_key_nvidea"))

client = QdrantClient("http://localhost:6333")
collection_name = "teste"

qdrant = Qdrant(
    client,
    collection_name,
    hf
)

base_retriever = qdrant.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 5},
)

retriever = base_retriever


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
    return {"message": "Hello World"}

@app.post("/chat")
async def chat(item: Item):
    query = item.query
    
    search_result = retriever.invoke(query)
    
    list_result = []
    context = ""
    mapping = {}
    
    for i, result in enumerate(search_result):
        context += f"Contexto {i}\n{result.page_content}\n\n"
        mapping[f"Contexto {i}"] = result.metadata.get("path")
        list_result.append({"id": i, "path": result.metadata.get("path"), "content": result.page_content})
    
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


    
    messages = [rolemsg, {"role": "user", "content": f"Documents:\n{context}\n\nQuestion: {query}"}]
    
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
    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)