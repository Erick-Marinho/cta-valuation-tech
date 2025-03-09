import PyPDF2
# import docx
from os import listdir
from os.path import isfile, join, isdir
from qdrant_client import QdrantClient
from langchain_text_splitters import TokenTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client.models import Distance, VectorParams
from langchain_qdrant import Qdrant


client = QdrantClient(url="http://localhost:6333")

#Listar diretórios e arquivos
def lista_arquivos(dir):
    arquivos_list = []
    
    for item in listdir(dir):
      if isfile(join(dir, item)):
        arquivos_list.append(join(dir, item))
      elif isdir(join(dir, item)):
         arquivos_list += lista_arquivos(join(dir, item))
    return arquivos_list

# Indexar chunks e metadata
def indexar_chunks(chunks, metadata):
  model_name = "sentence-transformers/msmarco-bert-base-dot-v5"
  model_kwargs = {"device": "cpu"}
  encode_kwargs = {"normalize_embeddings": True}
  
  hf = HuggingFaceEmbeddings(model_name = model_name, model_kwargs = model_kwargs, encode_kwargs = encode_kwargs) 
  client = QdrantClient(url="http://localhost:6333")
  collection_name = "teste"
  
  if client.collection_exists(collection_name):
    client.delete_collection(collection_name)
  
  client.create_collection(
    collection_name = collection_name,
    vectors_config = VectorParams(size = 768, distance = Distance.DOT)
  )
  
  qdrant = Qdrant(
    client,
    collection_name,
    hf
  )
  
  print(qdrant._embeddings)
  
  print("Indexando documentos...")
  
  qdrant.add_texts(chunks, metadatas = metadata)
  
  print("Documentos indexados com sucesso!")
  
#ler arquivos e dividir em chunks
def ler_arquivos(arquivos):
  for arquivo in arquivos:
    try:
      conteudo = ""
      
      if arquivo.endswith(".pdf"):
        print(f"Lendo arquivo PDF: {arquivo}")
        
        read = PyPDF2.PdfReader(arquivo)
        
        for page in read.pages:
          conteudo += " " + page.extract_text()
          
        result_split = TokenTextSplitter(chunk_size=500, chunk_overlap=50)
        
        chunks = result_split.split_text(conteudo)
        
        metadata = [{"path": arquivo} for _ in chunks]
        
        indexar_chunks(chunks, metadata)
    
    except Exception as e:
      print(f"Erro ao ler arquivo {arquivo}: {e}")
      
  
path_list = lista_arquivos("documents")
chuck_list = ler_arquivos(path_list)

 
# def get_embeddin():
#   all_points = client.scroll(
#     collection_name="teste",
#     limit=100,
#     with_vectors=True
#   )
  
#   return print(all_points)

# get_embeddin()


  
  
  





        
    
    
