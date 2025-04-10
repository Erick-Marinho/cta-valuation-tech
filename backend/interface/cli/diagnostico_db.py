import sys
import os
import logging
from pathlib import Path
import asyncio

# Adicionar o diretório raiz ao sys.path (PODE SER MANTIDO OU REMOVIDO SE -m FOR USADO)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")) # Ajustado para subir 2 níveis
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Importar APÓS ajustar o path
try:
    from config.config import Settings # Só precisamos de Settings aqui
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy.sql import text
    from sqlalchemy import select, func
    from infrastructure.persistence.sqlmodel.models import DocumentoDB # Manteve o caminho relativo a backend/
    from utils.logging import configure_logging # Necessário se o logger for usado ANTES do main_cli configurar
    from utils.telemetry import initialize_telemetry, get_tracer # Necessário se o tracer for usado ANTES do main_cli configurar
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode
except ImportError as e:
    print(f"Erro ao importar módulos em diagnostico_db.py: {e}")
    # Não sair mais com sys.exit, deixar main_cli tratar
    raise # Relançar a exceção para indicar falha no import

# --- Remover configuração de logging/telemetry daqui ---
# configure_logging() # FEITO EM MAIN_CLI
logger = logging.getLogger(__name__) # Apenas obter o logger
# settings = get_settings() # SETTINGS SERÃO PASSADAS COMO ARGUMENTO
# initialize_telemetry(...) # FEITO EM MAIN_CLI
# tracer = get_tracer(__name__) # OBTER TRACER DENTRO DA FUNÇÃO

# --- Modificar a função para aceitar settings ---
async def diagnosticar_sistema_rag(settings: Settings): # Adicionar settings como argumento
    """Executa verificações básicas de diagnóstico no banco de dados."""
    tracer = get_tracer(__name__) # Obter tracer aqui dentro
    with tracer.start_as_current_span("diagnosticar_sistema_rag") as span:
        span.set_attribute("command.name", "diagnose") # Adicionar atributo de comando
        print("\n====== DIAGNÓSTICO BÁSICO DO BANCO DE DADOS ======\n")
        engine = None
        try:
            # 1. Verificar conexão
            print("[1] Verificando conexão com o banco de dados via SQLAlchemy...")
            # Usar settings passado como argumento
            engine = create_async_engine(settings.DATABASE_URL, echo=False)
            AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

            async with AsyncSessionFactory() as session:
                async with session.begin():
                    result = await session.execute(text("SELECT 1"))
                    if result.scalar() == 1:
                        print("✅ Conexão com o banco de dados bem-sucedida!")
                        span.set_attribute("db.connection.status", "success")
                    else:
                         print("⚠️ Conexão com o banco de dados estabelecida, mas query de teste falhou.")
                         span.set_attribute("db.connection.status", "test_failed")

            # 2. Contar Documentos na Tabela 'documento'
            print("\n[2] Verificando contagem de documentos na tabela 'documento'...")
            async with AsyncSessionFactory() as session:
                async with session.begin():
                    stmt = select(func.count()).select_from(DocumentoDB)
                    result = await session.execute(stmt)
                    count = result.scalar_one_or_none()
                    if count is not None:
                        print(f"✅ Encontrados {count} documentos na tabela.")
                        span.set_attribute("db.document_count", count)
                    else:
                        print("⚠️ Não foi possível obter a contagem de documentos (resultado None).")
                        span.set_attribute("db.document_count", -1)

            print("\n====== DIAGNÓSTICO CONCLUÍDO ======")
            span.set_status(Status(StatusCode.OK))

        except Exception as e:
            print(f"❌ Erro durante o diagnóstico: {e}")
            logger.error(f"Erro no diagnóstico: {e}", exc_info=True)
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, f"Erro no diagnóstico: {e}"))
        finally:
            if engine:
                await engine.dispose()
                print("\nEngine do banco de dados finalizado.")

# --- REMOVER O BLOCO DE EXECUÇÃO DIRETA ---
# async def main():
#     await diagnosticar_sistema_rag()
#
# if __name__ == "__main__":
#     asyncio.run(main())
# -----------------------------------------
