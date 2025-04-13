# Usar a imagem oficial do MLflow como base
FROM ghcr.io/mlflow/mlflow:v2.15.0

# Instalar o driver psycopg2 (versão binária é mais fácil, não requer build)
RUN pip install psycopg2-binary

# O comando para rodar o servidor será definido no docker-compose.yml
