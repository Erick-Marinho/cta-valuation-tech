import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy import create_engine

from alembic import context

# Adicionar o diretório raiz do projeto (backend) ao sys.path
# para que possamos importar 'core'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.config import get_settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# Obter a URL do Banco das Configurações
settings = get_settings()
db_url = settings.DATABASE_URL
if not db_url:
    raise ValueError("DATABASE_URL not found in settings. Check your .env file.")

# Garantir que a URL use o driver +asyncpg para SQLAlchemy
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    alembic_db_url = db_url

    # Substituir o driver asyncpg pelo psycopg (v3) síncrono
    if alembic_db_url.startswith("postgresql+asyncpg://"):
        alembic_db_url = alembic_db_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1) # <-- Mudar para psycopg
    elif alembic_db_url.startswith("postgresql://"):
         alembic_db_url = alembic_db_url.replace("postgresql://", "postgresql+psycopg://", 1) # <-- Mudar para psycopg

    connectable = create_engine(
        alembic_db_url, # <-- URL com psycopg
        poolclass=pool.NullPool
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
