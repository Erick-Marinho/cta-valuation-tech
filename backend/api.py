import os
import dotenv
import uvicorn
from openai import OpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from langchain_qdrant import Qdrant
from pydantic import BaseModel
from fastapi import FastAPI
dotenv.load_dotenv()

class Item(BaseModel):
    query: str

model_name = "sentence-transformers/msmarco-bert-base-dot-v5"

model_kwargs = {"device": "cpu"}

encode_kwargs = {"normalize_embeddings": True}

hf = HuggingFaceEmbeddings(model_name = model_name, model_kwargs = model_kwargs, encode_kwargs = encode_kwargs) 

client_ai = OpenAI(base_url = "https://integrate.api.nvidia.com/v1",
  api_key = os.getenv("api_key_nvidea"))

client = QdrantClient("http://localhost:6333")
collection_name = "teste"

qdrant = Qdrant(
    client,
    collection_name,
    hf
  )

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/chat")
async def chat(item: Item):
  query = item.query
  
  search_result = qdrant.similarity_search(query = query, k = 10)
  
    
  list_result = []
  context = ""
  mapping = {}
  
  for i, result in enumerate(search_result):
    context += f"Contexto {i}\n{result.page_content}\n\n"
    mapping[f"Contexto {i}"] = result.metadata.get("path")
    list_result.append({"id": i, "path": result.metadata.get("path"), "content": result.page_content})
    
  rolemsg = {
    "role": "system",
    "content": f"Responda à pergunta do usuário usando documentos fornecidos no contexto. No contexto estão documentos que devem conter uma resposta.Use quantas citações e documentos forem necessários para responder à pergunta. As respostas serão em português brasil"
  }
  
  messages = [rolemsg, {"role": "user", "content": f"Documents:\n{context}\n\nQuestion: {query}"}]
  
  resposta = client_ai.chat.completions.create(
    model = "meta/llama3-70b-instruct",
    messages = messages,
    max_tokens = 1024,
    temperature = 0.3,
    stream = False
  )
  
  print(resposta)
  
  response = resposta.choices[0].message.content
  
  
  return {"response": response}
  
    

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
