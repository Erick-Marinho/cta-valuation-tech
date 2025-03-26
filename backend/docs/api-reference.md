# CTA Value Tech API - Documentação

## Visão Geral

A API CTA Value Tech é um serviço para valoração de tecnologias relacionadas ao Patrimônio Genético Nacional e Conhecimentos Tradicionais Associados. Baseada em uma arquitetura RAG (Retrieval-Augmented Generation), a API permite a consulta inteligente sobre documentos, gerando respostas contextualizadas usando modelos de linguagem avançados.

## Índice

1. [Arquitetura](#arquitetura)
2. [Autenticação](#autenticação)
3. [Endpoints](#endpoints)
    - [Health Check](#health-check)
    - [Chat](#chat)
    - [Documentos](#documentos)
4. [Modelos de Dados](#modelos-de-dados)
5. [Serviços Core](#serviços-core)
6. [Configuração](#configuração)
7. [Deployment](#deployment)

## Arquitetura

A API é construída com FastAPI e utiliza uma arquitetura em camadas:

- **API Layer**: Endpoints REST para interação com clientes
- **Service Layer**: Lógica de negócio e orquestração
- **Repository Layer**: Acesso e manipulação de dados
- **Infrastructure Layer**: Adaptadores para serviços externos (LLM, Embeddings)

O sistema usa PostgreSQL com a extensão pgvector para armazenamento eficiente de embeddings vetoriais, permitindo buscas semânticas de alta performance.

## Autenticação

A API suporta autenticação via API Key. A chave deve ser incluída no cabeçalho `X-API-Key` para endpoints protegidos. A autenticação pode ser ativada/desativada via configuração.

```python
# Exemplo de requisição autenticada
headers = {
    "X-API-Key": "your_api_key_here"
}
response = requests.post("https://api.example.com/documents/upload", headers=headers, files={"file": file})
```

## Endpoints

### Health Check

Endpoints para monitoramento da saúde e desempenho da aplicação.

#### GET /health

Verifica o status de saúde da aplicação e seus componentes.

**Resposta**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": 1647356457.123456,
  "components": {
    "database": {
      "status": "healthy"
    },
    "embedding_service": {
      "status": "healthy",
      "model": "intfloat/multilingual-e5-large-instruct"
    },
    "llm_service": {
      "status": "unknown"
    }
  }
}
```

#### GET /health/metrics

Retorna métricas detalhadas de desempenho e uso da aplicação.

**Resposta**:
```json
{
  "system": {
    "memory_usage_mb": 256.45,
    "cpu_percent": 12.5,
    "uptime_seconds": 3600,
    "python_version": "3.10.0",
    "platform": "Linux-5.4.0-1042-aws-x86_64-with-glibc2.31"
  },
  "database": {
    "status": "healthy"
  },
  "embedding": {
    "cache_size": 1024,
    "cache_hits": 450,
    "cache_misses": 50,
    "hit_rate": 0.9,
    "total_embeddings_generated": 500
  },
  "llm": {
    "requests_total": 100,
    "tokens_input_total": 25000,
    "tokens_output_total": 10000,
    "errors_total": 2,
    "avg_response_time": 1.25,
    "avg_tokens_per_request": 100,
    "error_rate": 0.02
  }
}
```

#### GET /health/ping

Endpoint simples para verificar se a API está respondendo.

**Resposta**:
```json
{
  "status": "ok",
  "message": "pong"
}
```

### Chat

Endpoints para conversação e consultas usando RAG.

#### POST /chat

Processa uma consulta do usuário usando o sistema RAG.

**Requisição**:
```json
{
  "query": "Como é feita a valoração de tecnologias com acesso ao Patrimônio Genético Nacional?",
  "document_ids": [1, 2, 3]
}
```

**Resposta**:
```json
{
  "response": "A valoração de tecnologias com acesso ao Patrimônio Genético Nacional envolve um processo multifacetado...",
  "processing_time": 2.35,
  "debug_info": {
    "query": "Como é feita a valoração de tecnologias com acesso ao Patrimônio Genético Nacional?",
    "clean_query": "valoração tecnologias acesso Patrimônio Genético Nacional",
    "num_results": 3,
    "sources": ["documento1.pdf", "documento2.pdf", "documento3.pdf"],
    "scores": [0.923, 0.875, 0.742]
  }
}
```

#### GET /chat/suggested-questions

Retorna perguntas sugeridas, opcionalmente baseadas em uma consulta do usuário.

**Parâmetros**:
- `query` (opcional): Consulta para basear as sugestões
- `limit` (opcional, padrão=5): Número máximo de sugestões

**Resposta**:
```json
[
  {
    "question": "O que é CTA Value Tech?"
  },
  {
    "question": "Como funciona a valoração de tecnologias?"
  },
  {
    "question": "Quais são os indicadores de sustentabilidade utilizados?"
  }
]
```

### Documentos

Endpoints para gerenciamento de documentos.

#### GET /documents

Lista todos os documentos disponíveis.

**Parâmetros**:
- `limit` (opcional, padrão=10): Número máximo de resultados
- `offset` (opcional, padrão=0): Offset para paginação
- `sort_by` (opcional): Campo para ordenação
- `order` (opcional, padrão="asc"): Ordem de classificação (asc ou desc)
- `name_filter` (opcional): Filtrar por nome do documento

**Resposta**:
```json
{
  "documents": [
    {
      "id": 1,
      "name": "documento_valoracao.pdf",
      "file_type": "pdf",
      "upload_date": "2023-03-15T14:30:45.123456",
      "size_kb": 1024.5,
      "chunks_count": 15,
      "processed": true,
      "metadata": {
        "author": "João Silva",
        "title": "Valoração de PGN",
        "pages": 25
      }
    }
  ],
  "total": 45,
  "limit": 10,
  "offset": 0
}
```

#### POST /documents/upload

Faz upload e processa um novo documento.

**Requisição**:
- Formulário multipart com campo `file` contendo o arquivo PDF

**Resposta**:
```json
{
  "id": 5,
  "name": "novo_documento.pdf",
  "file_type": "pdf",
  "size_kb": 2048.75,
  "chunks_count": 23,
  "processed": true,
  "message": "Documento processado com sucesso"
}
```

#### GET /documents/{document_id}

Obtém informações sobre um documento específico.

**Parâmetros**:
- `document_id`: ID do documento

**Resposta**:
```json
{
  "id": 5,
  "name": "documento_detalhado.pdf",
  "file_type": "pdf",
  "upload_date": "2023-03-15T14:30:45.123456",
  "size_kb": 1024.5,
  "chunks_count": 15,
  "processed": true,
  "metadata": {
    "author": "Maria Santos",
    "title": "Análise de Tecnologias CTA",
    "pages": 42
  }
}
```

#### DELETE /documents/{document_id}

Exclui um documento pelo ID.

**Parâmetros**:
- `document_id`: ID do documento a ser excluído

**Resposta**:
```json
{
  "message": "Documento 5 excluído com sucesso"
}
```

## Modelos de Dados

### ChatQuery
```json
{
  "query": "string",
  "document_ids": [1, 2, 3]
}
```

### ChatResponse
```json
{
  "response": "string",
  "processing_time": 1.23,
  "debug_info": {
    "query": "string",
    "clean_query": "string",
    "num_results": 3,
    "sources": ["string"],
    "scores": [0.9, 0.8, 0.7]
  }
}
```

### DocumentResponse
```json
{
  "id": 1,
  "name": "string",
  "file_type": "string",
  "upload_date": "2023-03-15T14:30:45.123456",
  "size_kb": 1024.5,
  "chunks_count": 15,
  "processed": true,
  "metadata": {}
}
```

### HealthResponse
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": 1647356457.123456,
  "components": {}
}
```

## Serviços Core

A API utiliza vários serviços centrais para seu funcionamento:

### EmbeddingService

Responsável por gerar e gerenciar embeddings vetoriais para textos. Utiliza modelos da HuggingFace e implementa um sistema de cache para otimização.

### LLMService

Serviço para geração de texto com modelos de linguagem. Integra-se com a API da NVIDIA para acessar modelos como o LLaMA3.

### RAGService

Orquestra o processo completo de Retrieval-Augmented Generation:
1. Preparação e limpeza da consulta
2. Geração de embeddings
3. Recuperação de documentos relevantes
4. Montagem do contexto para o LLM
5. Geração da resposta

### DocumentService

Gerencia o processamento completo de documentos:
1. Extração de texto
2. Chunking (divisão em partes gerenciáveis)
3. Geração de embeddings
4. Armazenamento

## Configuração

A API utiliza variáveis de ambiente para configuração, que podem ser definidas diretamente ou via arquivo `.env`:

```
# Configurações da aplicação
APP_NAME="CTA Value Tech"
APP_VERSION="1.0.0"
DEBUG=false

# Configuração do banco de dados
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/vectordb
AUTO_INIT_DB=true

# Configuração do modelo de embeddings
EMBEDDING_MODEL=intfloat/multilingual-e5-large-instruct
EMBEDDING_DIMENSION=1024
USE_GPU=true

# Configuração de processamento de texto
CHUNK_SIZE=800
CHUNK_OVERLAP=100

# Configurações de servidor
PORT=8000
CORS_ORIGINS=["*"]

# API da NVIDIA para LLM
API_KEY_NVIDEA=your_key_here

# Autenticação (opcional)
API_KEY=your_api_key_here

# Logging
LOG_LEVEL=INFO
```

## Deployment

A aplicação está configurada para deployment via Docker. Um Dockerfile e docker-compose.yml estão disponíveis para facilitar a implantação.

### Usando Docker Compose

```bash
docker-compose up -d
```

### Construindo a imagem manualmente

```bash
docker build -t cta-value-tech .
docker run -p 8000:8000 -d cta-value-tech
```