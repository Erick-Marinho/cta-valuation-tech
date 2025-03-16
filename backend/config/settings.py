"""
Configurações gerais da aplicação RAG.
Centraliza todas as configurações não sensíveis do sistema.
"""

# Configurações do modelo de embeddings
EMBEDDING_MODEL = {
    "model_name": "intfloat/multilingual-e5-large-instruct",
    "model_kwargs": {"device": "cpu"},
    "encode_kwargs": {"normalize_embeddings": True}
}

# Configurações de processamento de documentos
DOCUMENT_PROCESSING = {
    "supported_file_types": ["pdf"],  # Tipos de arquivo suportados
    "chunk_size": 800,               # Tamanho padrão dos chunks de texto
    "chunk_overlap": 100              # Sobreposição entre chunks
}

# Configurações do banco de dados
DATABASE = {
    "tables": {
        "documentos_originais": "documentos_originais",
        "chunks_vetorizados": "chunks_vetorizados"
    }
}

# Configurações de diretórios
DIRECTORIES = {
    "documents": "documents",  # Diretório padrão para documentos
    "temp": "temp"            # Diretório para arquivos temporários
} 