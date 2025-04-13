import argparse
import asyncio
import logging
import dotenv
import os # Se necessário

# Importar get_settings (ajustar caminho se necessário)
from config.config import get_settings, Settings # Importar Settings também se usado abaixo
# --- Importar as funções de comando REAIS ---
from .migrate_command import migrar_documentos
from .search_command import testar_busca
# --- Adicionar import do diagnóstico ---
from .diagnostico_db import diagnosticar_sistema_rag

# --- Importar configuração e inicialização ---
# (Imports atualizados para infrastructure)
from infrastructure.logging.config import configure_logging # <-- Corrigido
from infrastructure.telemetry.opentelemetry import initialize_telemetry # <-- Corrigido

# -------------------------------------------------------------

logger = logging.getLogger(__name__)

async def main(settings: Settings): # <-- Receber settings como argumento
    """Função principal do script CLI."""
    parser = argparse.ArgumentParser( description="Ferramenta para migração, busca e diagnóstico RAG" ) # Descrição atualizada
    subparsers = parser.add_subparsers(dest="comando", help="Comandos disponíveis", required=True)

    migrate_parser = subparsers.add_parser( "migrate", help="Migrar documentos para o banco de dados" )
    migrate_parser.add_argument( "--dir", type=str, default="documents", help="Diretório de documentos" )

    search_parser = subparsers.add_parser("search", help="Testar busca RAG")
    search_parser.add_argument( "query", type=str, nargs="?", default="O que é repartição de benefícios?", help="Consulta para teste", )

    # --- Parser para 'diagnose' (novo) ---
    diagnose_parser = subparsers.add_parser("diagnose", help="Executar diagnóstico do banco de dados")
    # Não precisa de argumentos específicos por enquanto

    args = parser.parse_args()

    # Settings agora são recebidos como argumento
    # settings = get_settings() # <-- Remover busca redundante

    # O logger já deve estar configurado pelo __main__
    logger.info(f"Executando comando CLI: {args.comando}")

    try:
        if args.comando == "migrate":
            await migrar_documentos(settings, args.dir) # Passar settings
        elif args.comando == "search":
            await testar_busca(settings, args.query) # Passar settings
        elif args.comando == "diagnose":
            await diagnosticar_sistema_rag(settings) # Passar settings
    except Exception as main_exc:
            logger.error(f"Erro na execução do comando {args.comando}: {main_exc}", exc_info=True)

if __name__ == "__main__":
    # --- Configuração Inicial Centralizada ---
    print("Configurando ambiente para CLI...")
    dotenv.load_dotenv()
    # Chamar configuração de log (import corrigido)
    configure_logging()
    # Carregar settings APÓS dotenv
    try:
        settings = get_settings()
    except Exception as e:
        print(f"ERRO CRÍTICO AO CARREGAR SETTINGS: {e}")
        exit(1)

    # Inicializar telemetria (import corrigido)
    try:
        initialize_telemetry(service_name=settings.OTEL_SERVICE_NAME + "-cli")
    except Exception as e:
        print(f"ERRO AO INICIALIZAR TELEMETRIA: {e}")
    # -----------------------------------------

    try:
        print("Executando CLI a partir de main_cli.py...")
        # Passar settings para a função main
        asyncio.run(main(settings))
    except KeyboardInterrupt:
        print("\nExecução da CLI interrompida.")
    except Exception as e:
         logger = logging.getLogger(__name__)
         logger.critical(f"Erro fatal não capturado na inicialização da CLI: {e}", exc_info=True)
