import PyPDF2
import os
from os import listdir
from os.path import isfile, join, isdir
from qdrant_client import QdrantClient
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client.models import Distance, VectorParams
from langchain_qdrant import QdrantVectorStore


def lista_arquivos(dir):
    """Listar todos os arquivos em um diretório e seus subdiretórios."""
    arquivos_list = []

    for item in listdir(dir):
        if isfile(join(dir, item)):
            arquivos_list.append(join(dir, item))
        elif isdir(join(dir, item)):
            arquivos_list += lista_arquivos(join(dir, item))
    return arquivos_list

def preparar_vectorstore(collection_name="teste"):
    """Prepara e retorna o QdrantVectorStore."""
    model_name = "intfloat/multilingual-e5-large-instruct"
    model_kwargs = {"device": "cpu"}
    encode_kwargs = {"normalize_embeddings": True}

    hf = HuggingFaceEmbeddings(
        model_name=model_name, 
        model_kwargs=model_kwargs, 
        encode_kwargs=encode_kwargs
    ) 
    
    client = QdrantClient(url="http://localhost:6333")
    
    # Apagar e recriar a coleção apenas uma vez no início
    if client.collection_exists(collection_name):
        print(f"Apagando coleção existente: {collection_name}")
        client.delete_collection(collection_name)
    
    print(f"Criando nova coleção: {collection_name}")
    vector_params = VectorParams(
        size=1024,  # Tamanho do vetor de embedding
        distance=Distance.COSINE  # Métrica de distância
    )
    
    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=vector_params
    )
    
    qdrant = QdrantVectorStore(
        client,
        collection_name,
        hf
    )
    
    return qdrant

def processar_arquivo(arquivo, qdrant):
    """Processa um único arquivo e retorna chunks e metadados."""
    print(f"Processando arquivo: {arquivo}")
    chunks = []
    metadata = []
    
    try:
        conteudo = ""
        
        if arquivo.endswith(".pdf"):
            print(f"Lendo arquivo PDF: {arquivo}")
            try:
                read = PyPDF2.PdfReader(arquivo)
                for page in read.pages:
                    texto_pagina = page.extract_text()
                    if texto_pagina:  # Verifica se o texto não está vazio
                        conteudo += " " + texto_pagina
            except Exception as e:
                print(f"Erro ao ler PDF {arquivo}: {e}")
                return [], []
        
        # Adicione aqui suporte para outros tipos de arquivo
        # elif arquivo.endswith(".txt"):
        #     with open(arquivo, 'r', encoding='utf-8') as f:
        #         conteudo = f.read()
        # elif arquivo.endswith(".docx"):
        #     # Implemente a leitura de arquivos DOCX
        
        else:
            print(f"Tipo de arquivo não suportado: {arquivo}")
            return [], []
        
        if not conteudo.strip():  # Verifica se o conteúdo está vazio após processamento
            print(f"Aviso: Conteúdo vazio extraído de {arquivo}")
            return [], []
        
        # Dividir texto em chunks
        result_split = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", " ", ""],
            is_separator_regex=False
        )
        
        chunks = result_split.split_text(conteudo)
        if not chunks:
            print(f"Aviso: Nenhum chunk gerado para {arquivo}")
            return [], []
            
        print(f"Gerados {len(chunks)} chunks para {arquivo}")
        metadata = [{"path": arquivo, "chunk_id": i} for i, _ in enumerate(chunks)]
        
    except Exception as e:
        print(f"Erro ao processar arquivo {arquivo}: {e}")
        return [], []
    
    return chunks, metadata

def indexar_documentos(dir_documentos="documents", collection_name="teste", batch_size=100):
    """Processa e indexa todos os documentos do diretório especificado."""
    # Obter lista de arquivos
    arquivos = lista_arquivos(dir_documentos)
    print(f"Encontrados {len(arquivos)} arquivos em {dir_documentos}")
    
    if not arquivos:
        print("Nenhum arquivo encontrado para processamento")
        return
    
    # Preparar o vector store (apenas uma vez)
    qdrant = preparar_vectorstore(collection_name)
    print(f"Vector store configurado com o modelo de embeddings: {qdrant._embeddings}")
    
    # Processar arquivos em batch para melhor performance
    todos_chunks = []
    todos_metadata = []
    arquivos_processados = 0
    arquivos_com_erro = 0
    total_chunks = 0
    
    for arquivo in arquivos:
        chunks, metadata = processar_arquivo(arquivo, qdrant)
        
        if chunks:  # Se tiver chunks válidos
            todos_chunks.extend(chunks)
            todos_metadata.extend(metadata)
            total_chunks += len(chunks)
            arquivos_processados += 1
            
            # Indexar em batches para não sobrecarregar a memória
            if len(todos_chunks) >= batch_size:
                print(f"Indexando batch de {len(todos_chunks)} chunks...")
                qdrant.add_texts(todos_chunks, metadatas=todos_metadata)
                todos_chunks = []
                todos_metadata = []
        else:
            arquivos_com_erro += 1
    
    # Indexar os chunks restantes
    if todos_chunks:
        print(f"Indexando batch final de {len(todos_chunks)} chunks...")
        qdrant.add_texts(todos_chunks, metadatas=todos_metadata)
    
    print("\n--- Resumo da Indexação ---")
    print(f"Total de arquivos encontrados: {len(arquivos)}")
    print(f"Arquivos processados com sucesso: {arquivos_processados}")
    print(f"Arquivos com erro ou não suportados: {arquivos_com_erro}")
    print(f"Total de chunks indexados: {total_chunks}")
    print("Indexação concluída com sucesso!")
    
    return qdrant

# Execução principal
if __name__ == "__main__":
    indexar_documentos("documents")