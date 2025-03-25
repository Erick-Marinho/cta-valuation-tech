-- Criar extensão pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Tabela para armazenar os documentos originais
CREATE TABLE IF NOT EXISTS documentos_originais (
    id SERIAL PRIMARY KEY,
    nome_arquivo TEXT NOT NULL,
    tipo_arquivo TEXT NOT NULL,
    conteudo_binario BYTEA NOT NULL,
    data_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadados JSONB
);

-- Tabela para armazenar os chunks vetorizados
CREATE TABLE IF NOT EXISTS chunks_vetorizados (
    id SERIAL PRIMARY KEY,
    documento_id INTEGER REFERENCES documentos_originais(id) ON DELETE CASCADE,
    texto TEXT NOT NULL,
    embedding vector(1024),
    pagina INTEGER,
    posicao INTEGER,
    metadados JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índice para busca vetorial mais rápida
CREATE INDEX IF NOT EXISTS chunks_embedding_idx ON chunks_vetorizados USING ivfflat (embedding vector_cosine_ops);