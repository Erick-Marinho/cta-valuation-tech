import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context

# --- 1. Configuração do Caminho para Importação ---
# Adicionar o diretório raiz do projeto (backend) ao sys.path
# para que possamos importar módulos da aplicação como 'config' e 'infrastructure'.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- 2. Importar Modelos e Configurações ---
# Importar a classe base SQLModel (ou modelos específicos) para obter o metadata.
# Isso é essencial para o Alembic --autogenerate funcionar.
from infrastructure.persistence.sqlmodel.models import SQLModel
# Importar configurações para obter a URL do banco de dados.
from config.config import get_settings

# --- 3. Configuração do Alembic ---
# Objeto de configuração do Alembic, lê do alembic.ini
config = context.config

# Configurar logging a partir do arquivo .ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Definir o target_metadata para o autogenerate usar.
# Deve ser o MetaData dos seus modelos SQLModel/SQLAlchemy.
target_metadata = SQLModel.metadata

# --- 4. Configuração da URL do Banco de Dados ---
settings = get_settings()
db_url = settings.DATABASE_URL
if not db_url:
    raise ValueError("DATABASE_URL não encontrada nas configurações. Verifique seu .env.")

# --- 5. Funções de Migração ---

def run_migrations_offline() -> None:
    """
    Executa migrações em modo 'offline'.
    Gera scripts SQL sem se conectar ao banco de dados.
    """
    print("Executando migrações em modo offline...")
    # Usar a URL original das configurações (pode ser async)
    context.configure(
        url=db_url,
        target_metadata=target_metadata, # Usar o metadata definido acima
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()
    print("Migrações offline concluídas.")


def run_migrations_online() -> None:
    """
    Executa migrações em modo 'online'.
    Conecta-se ao banco de dados e aplica as migrações.
    """
    print("Executando migrações em modo online...")
    # Preparar URL para conexão síncrona:
    # Alembic precisa de um driver DBAPI síncrono (como psycopg ou psycopg2).
    # Substituímos o driver async (asyncpg) pelo sync (psycopg).
    online_db_url = db_url
    if online_db_url.startswith("postgresql+asyncpg://"):
        online_db_url = online_db_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    elif online_db_url.startswith("postgresql://"):
        # Se não especificar driver, assume psycopg por padrão no SQLAlchemy >= 2.0 com create_engine
        online_db_url = online_db_url.replace("postgresql://", "postgresql+psycopg://", 1) # Ser explícito

    print(f"Usando URL síncrona para Alembic: {online_db_url.replace(settings.DB_PASSWORD, '***') if settings.DB_PASSWORD else online_db_url}")

    # Usar engine_from_config é geralmente recomendado se você tiver
    # configurações de pool, etc., no alembic.ini, mas create_engine é mais direto aqui.
    # connectable = engine_from_config(
    #     config.get_section(config.config_ini_section, {}), # Ler do alembic.ini
    #     prefix="sqlalchemy.",
    #     poolclass=pool.NullPool,
    #     url=online_db_url # Sobrescrever URL se necessário
    # )
    # Alternativa mais simples usando create_engine diretamente:
    connectable = create_engine(online_db_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        print("Conexão com o banco estabelecida.")
        context.configure(
            connection=connection,
            target_metadata=target_metadata # Usar o metadata definido acima
            # Remover context_kwargs se não estiver definido/utilizado
        )
        print("Contexto Alembic configurado.")

        # Transações são importantes para garantir consistência
        with context.begin_transaction():
            print("Iniciando transação de migração...")
            context.run_migrations()
            print("Comandos de migração executados.")

    print("Migrações online concluídas.")
    connectable.dispose() # Fechar a engine síncrona


# --- 6. Execução Principal ---
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
