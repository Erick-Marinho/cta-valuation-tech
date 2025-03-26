FROM python:3.11.5-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    inotify-tools \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    WATCHFILES_FORCE_POLLING=true \
    WATCHFILES_POLL_INTERVAL=0.1

# Copiar requisitos primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Criar diretório para arquivos processados
RUN mkdir -p /app/backend/documents

# Copiar o código da aplicação
COPY . .

# Expor a porta da aplicação
EXPOSE 8000

# Criar usuário não privilegiado e configurar permissões
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app && \
    chown -R appuser:appuser /app/documents && \
    chmod -R 755 /app/documents

# Mudar para o usuário não privilegiado
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health/ping || exit 1

# Comando para iniciar a aplicação
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]