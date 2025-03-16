"""
Gerenciamento de variáveis de ambiente para a aplicação RAG.
Carrega e valida todas as variáveis de ambiente necessárias.
"""

import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Configurações do Banco de Dados
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "port": int(os.getenv("DB_PORT", "5432"))
}

# Configurações de API
API_CONFIG = {
    "host": os.getenv("API_HOST", "0.0.0.0"),
    "port": int(os.getenv("API_PORT", "8000")),
    "debug": os.getenv("DEBUG", "False").lower() == "true"
}

def validate_environment():
    """Valida se todas as variáveis de ambiente necessárias estão configuradas."""
    required_vars = [
        "DB_PASSWORD",  # Senha do banco de dados é obrigatória
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise EnvironmentError(
            f"As seguintes variáveis de ambiente são obrigatórias: {', '.join(missing_vars)}"
        )

# Valida as variáveis de ambiente ao importar o módulo
#validate_environment() 