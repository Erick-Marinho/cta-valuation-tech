# Guia de Início Rápido

Este guia fornece as instruções básicas para começar a utilizar a API CTA Value Tech.

## Pré-requisitos

- Python 3.10 ou superior
- PostgreSQL 13 ou superior com a extensão pgvector instalada
- Chave de API da NVIDIA para acesso aos modelos LLM (opcional, mas recomendado para funcionalidade completa)

## Configuração do Ambiente

1. **Clone o repositório**

```bash
git clone https://github.com/sua-organizacao/cta-value-tech.git
cd cta-value-tech
```

2. **Configure o ambiente virtual**

```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
```

3. **Configure as variáveis de ambiente**

Crie um arquivo `.env` na pasta `backend/` com o seguinte conteúdo:

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
USE_GPU=false

# Configuração de processamento de texto
CHUNK_SIZE=800
CHUNK_OVERLAP=100

# Configurações de servidor
PORT=8000
CORS_ORIGINS=["*"]

# API da NVIDIA para LLM
API_KEY_NVIDEA=sua_chave_aqui

# Autenticação (opcional)
API_KEY=sua_api_key_aqui

# Logging
LOG_LEVEL=INFO
```

4. **Inicialize o banco de dados**

Certifique-se de que o PostgreSQL está rodando e crie o banco de dados:

```bash
psql -U postgres -c "CREATE DATABASE vectordb;"
psql -U postgres -d vectordb -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

5. **Execute a aplicação**

```bash
cd backend
uvicorn app:app --reload
```

A API estará disponível em `http://localhost:8000`.

## Testando a API

### Verificar se a API está funcionando

```bash
curl http://localhost:8000/health/ping
```

Você deverá receber:

```json
{"status":"ok","message":"pong"}
```

### Verificar a saúde dos componentes

```bash
curl http://localhost:8000/health
```

### Importar um documento de teste

```bash
curl -X POST -H "X-API-Key: sua_api_key_aqui" \
  -F "file=@seu_documento.pdf" \
  http://localhost:8000/documents/upload
```

### Fazer uma consulta

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"query":"Como funciona a valoração de tecnologias?"}' \
  http://localhost:8000/chat/
```

## Documentação Interativa

A API inclui documentação interativa gerada automaticamente pelo FastAPI, disponível em:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Estas interfaces permitem explorar todos os endpoints, testar chamadas à API diretamente no navegador e visualizar os modelos de dados.

## Próximos Passos

- Consulte a [Referência da API](api-reference.md) para detalhes completos sobre todos os endpoints
- Veja o [Guia de Desenvolvimento](development-guide.md) para entender a estrutura do código
- Confira as [Instruções de Implantação](deployment.md) para informações sobre deployment em produção