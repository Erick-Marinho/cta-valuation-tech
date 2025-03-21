# Instruções de Implantação

Este documento contém instruções detalhadas para implantar a API CTA Value Tech em diferentes ambientes.

## Implantação com Docker (Recomendado)

A forma mais simples de implantar a API é utilizando Docker e Docker Compose.

### Pré-requisitos

- Docker 20.10 ou superior
- Docker Compose v2.0 ou superior
- No mínimo 4GB de RAM disponível para os containers
- No mínimo 20GB de espaço em disco

### Passos para Implantação

1. **Clone o repositório**:

```bash
git clone https://github.com/sua-organizacao/cta-value-tech.git
cd cta-value-tech
```

2. **Configure as variáveis de ambiente**:

Crie um arquivo `.env` na raiz do projeto:

```
# Configurações da aplicação
APP_NAME=CTA Value Tech
APP_VERSION=1.0.0
DEBUG=false

# Configuração do banco de dados
DATABASE_URL=postgresql://postgres:postgres@db:5432/vectordb
AUTO_INIT_DB=true

# Configuração do modelo de embeddings
EMBEDDING_MODEL=intfloat/multilingual-e5-large-instruct
EMBEDDING_DIMENSION=1024
USE_GPU=false

# API da NVIDIA para LLM
API_KEY_NVIDEA=sua_chave_aqui

# Autenticação
API_KEY=sua_api_key_aqui
```

3. **Inicie os containers**:

```bash
docker-compose up -d
```

4. **Verifique se a aplicação está rodando**:

```bash
curl http://localhost:8000/health/ping
```

### Escalar a Aplicação

Para escalar a aplicação horizontalmente:

```bash
docker-compose up -d --scale backend=3
```

Isso criará três instâncias do serviço backend. Neste caso, você precisará usar um load balancer como Nginx ou Traefik na frente dos containers.

## Implantação em Kubernetes

Para ambientes de produção, recomendamos implantação em Kubernetes.

### Pré-requisitos

- Cluster Kubernetes 1.20 ou superior
- kubectl configurado
- Helm 3.0 ou superior

### Passos para Implantação

1. **Prepare as configurações**:

Crie um arquivo `values.yaml`:

```yaml
replicaCount: 2

image:
  repository: seuregistry/cta-value-tech
  tag: latest
  pullPolicy: Always

environment:
  APP_NAME: "CTA Value Tech"
  APP_VERSION: "1.0.0"
  DEBUG: "false"
  DATABASE_URL: "postgresql://postgres:postgres@postgres-service:5432/vectordb"
  EMBEDDING_MODEL: "intfloat/multilingual-e5-large-instruct"
  EMBEDDING_DIMENSION: "1024"
  USE_GPU: "false"

secret:
  API_KEY_NVIDEA: "sua_chave_aqui"
  API_KEY: "sua_api_key_aqui"

service:
  type: ClusterIP
  port: 8000

resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    cpu: 2000m
    memory: 4Gi

postgresql:
  enabled: true
  postgresqlUsername: postgres
  postgresqlPassword: postgres
  postgresqlDatabase: vectordb
  persistence:
    size: 20Gi
```

2. **Implante usando Helm**:

```bash
helm install cta-value-tech ./helm-chart -f values.yaml
```

3. **Verifique a implantação**:

```bash
kubectl get pods
kubectl get svc
```

## Implantação Manual

Se você preferir uma implantação manual em um servidor, siga estas instruções:

### Pré-requisitos

- Ubuntu 20.04 LTS ou superior
- Python 3.10 ou superior
- PostgreSQL 13 ou superior com pgvector
- Nginx (opcional, para proxy reverso)

### Passos de Instalação

1. **Atualize o sistema**:

```bash
sudo apt update && sudo apt upgrade -y
```

2. **Instale as dependências**:

```bash
sudo apt install -y python3-pip python3-venv postgresql nginx
```

3. **Configure o PostgreSQL**:

```bash
sudo -u postgres psql -c "CREATE DATABASE vectordb;"
sudo -u postgres psql -c "CREATE USER appuser WITH PASSWORD 'senha_segura';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE vectordb TO appuser;"
sudo -u postgres psql -d vectordb -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

4. **Configure a aplicação**:

```bash
# Clone o repositório
git clone https://github.com/sua-organizacao/cta-value-tech.git
cd cta-value-tech

# Configure o ambiente virtual
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# Configure as variáveis de ambiente
cp backend/.env.example backend/.env
# Edite o arquivo .env com seus valores
```

5. **Configure o serviço systemd**:

Crie um arquivo `/etc/systemd/system/cta-value-tech.service`:

```
[Unit]
Description=CTA Value Tech API
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/caminho/para/cta-value-tech/backend
Environment="PATH=/caminho/para/cta-value-tech/venv/bin"
EnvironmentFile=/caminho/para/cta-value-tech/backend/.env
ExecStart=/caminho/para/cta-value-tech/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

6. **Ative e inicie o serviço**:

```bash
sudo systemctl daemon-reload
sudo systemctl enable cta-value-tech
sudo systemctl start cta-value-tech
```

7. **Configure o Nginx (opcional)**:

Crie um arquivo `/etc/nginx/sites-available/cta-value-tech`:

```
server {
    listen 80;
    server_name seu-dominio.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Ative o site:

```bash
sudo ln -s /etc/nginx/sites-available/cta-value-tech /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Monitoramento

### Verificação de Saúde

A API fornece endpoints para monitoramento:

- `/health/ping` - Teste simples de conectividade
- `/health` - Estado de saúde de todos os componentes
- `/health/metrics` - Métricas detalhadas de performance

### Integração com Prometheus (opcional)

Para monitoramento avançado, você pode integrar a API com Prometheus:

1. Instale o prometheus-client:

```bash
pip install prometheus-client
```

2. Configure o endpoint de métricas no arquivo `app.py`:

```python
from prometheus_client import make_asgi_app

# Crie um endpoint de métricas Prometheus
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

3. Configure o Prometheus para coletar métricas do endpoint.

## Backup e Recuperação

### Backup do Banco de Dados

Crie backups regulares do PostgreSQL:

```bash
pg_dump -U postgres -d vectordb -F c -f backup_$(date +%Y%m%d).dump
```

### Recuperação

Para restaurar um backup:

```bash
pg_restore -U postgres -d vectordb -c backup_20230101.dump
```

## Atualizações

Para atualizar a aplicação para uma nova versão:

1. **Backup dos dados**:
```bash
pg_dump -U postgres -d vectordb -F c -f backup_antes_atualizacao.dump
```

2. **Atualização via Docker**:
```bash
git pull
docker-compose down
docker-compose build
docker-compose up -d
```

3. **Atualização manual**:
```bash
git pull
source venv/bin/activate
pip install -r backend/requirements.txt
sudo systemctl restart cta-value-tech
```

## Resolução de Problemas

### Logs do Docker
```bash
docker-compose logs -f backend
```

### Logs do Serviço Systemd
```bash
journalctl -u cta-value-tech.service -f
```

### Problemas Comuns

1. **Erro de conexão com o banco de dados**:
   - Verifique se a URL do banco de dados está correta
   - Verifique se o banco de dados está acessível

2. **Erro na inicialização dos modelos de embedding**:
   - Verifique se há espaço suficiente em disco
   - Verifique se as credenciais da API da NVIDIA são válidas

3. **API lenta**:
   - Verifique a utilização de recursos (CPU/memória)
   - Considere escalar horizontalmente ou verticalmente
   - Verifique o tamanho dos chunks e ajuste se necessário

Para problemas adicionais, consulte o registro de logs ou abra uma issue no repositório do projeto.