import subprocess
import os

# Obter o diretório do projeto
project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
mlflow_dir = os.path.join(project_dir, "infrastructure", "mlflow")

# Verificar se o diretório existe
if not os.path.exists(mlflow_dir):
    os.makedirs(mlflow_dir)

# Configurar o comando MLflow
tracking_uri = f"file://{mlflow_dir}"
command = ["mlflow", "ui", "--backend-store-uri", tracking_uri]

# Executar a UI
print(f"Iniciando MLflow UI com tracking URI: {tracking_uri}")
subprocess.run(command) 