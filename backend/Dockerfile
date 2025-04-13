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
    WATCHFILES_POLL_INTERVAL=0.1 \
    NLTK_DATA=/app/nltk_data

# Criar usuário não privilegiado ANTES de precisar dele para permissões
RUN useradd -m -u 1000 appuser

# Copiar requisitos primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instalar dependências Python (nltk será instalado aqui)
RUN pip install --no-cache-dir --pre -r requirements.txt

# Criar diretório para arquivos processados
RUN mkdir -p /app/documents && chown appuser:appuser /app/documents

# Criar o diretório para os dados do NLTK E DEFINIR PERMISSÃO
RUN mkdir -p $NLTK_DATA && chown appuser:appuser $NLTK_DATA

# Copiar o código da aplicação E OS SCRIPTS
# A pasta 'scripts/' na raiz será copiada para '/app/scripts/'
COPY . .

# Executar o script de download após copiar o código e instalar dependências
# Idealmente, o script de download também deveria rodar como appuser se possível,
# ou garantir que os dados baixados tenham as permissões corretas.
# Por simplicidade, deixamos como root por enquanto, mas o chown acima garante que
# o diretório NLTK_DATA pertence ao appuser.
RUN python scripts/download_nltk.py

# --- MOVER CHOWN GERAL PARA DEPOIS DE COPIAR TUDO ---
# Garante que todo o código copiado pertença ao appuser
RUN chown -R appuser:appuser /app
# ---------------------------------------------------

# Expor a porta da aplicação
EXPOSE 8000

# Health check (deve rodar como root ou garantir que curl esteja disponível para appuser)
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health/ping || exit 1

# Mudar para o usuário não privilegiado NO FINAL
USER appuser

# Comando para iniciar a aplicação (agora roda como appuser)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]