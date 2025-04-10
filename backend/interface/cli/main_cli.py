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
# (Assumindo que estas funções/módulos existem em utils)
from utils.logging import configure_logging
from utils.telemetry import initialize_telemetry

# -------------------------------------------------------------

logger = logging.getLogger(__name__)

async def main():
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

    # Settings agora é carregado no __main__ antes de chamar main()
    # Mas pode ser passado como argumento ou acessado globalmente se necessário
    # Para simplificar, vamos buscar novamente aqui por enquanto
    # Idealmente, seria passado como argumento para 'main'
    settings = get_settings()

    # O logger já deve estar configurado pelo __main__
    logger.info(f"Executando comando CLI: {args.comando}")

    try:
        if args.comando == "migrate":
            await migrar_documentos(settings, args.dir)
        elif args.comando == "search":
            await testar_busca(settings, args.query)
        # --- Adicionar chamada para diagnose ---
        elif args.comando == "diagnose":
            await diagnosticar_sistema_rag(settings) # Passar settings
    except Exception as main_exc:
            # Usar logger configurado
            logger.error(f"Erro na execução do comando {args.comando}: {main_exc}", exc_info=True)

if __name__ == "__main__":
    # --- Configuração Inicial Centralizada ---
    print("Configurando ambiente para CLI...")
    dotenv.load_dotenv()
    # Chame sua função de configuração de log aqui
    # Certifique-se que a função configure_logging existe em utils/logging.py
    configure_logging()
    # Carregar settings APÓS dotenv para pegar variáveis do .env
    try:
        settings = get_settings()
    except Exception as e:
        # Logger pode não estar configurado ainda, usar print
        print(f"ERRO CRÍTICO AO CARREGAR SETTINGS: {e}")
        exit(1) # Sair se não conseguir carregar settings

    # Inicializar telemetria (se aplicável à CLI)
    # Certifique-se que a função initialize_telemetry existe em utils/telemetry.py
    try:
        initialize_telemetry(service_name=settings.OTEL_SERVICE_NAME + "-cli")
    except Exception as e:
        # Logger pode não estar configurado ainda, usar print
        print(f"ERRO AO INICIALIZAR TELEMETRIA: {e}")
        # Continuar execução mesmo se telemetria falhar? Ou sair?
    # -----------------------------------------

    try:
        print("Executando CLI a partir de main_cli.py...")
        asyncio.run(main()) # 'main' agora usará as settings já carregadas implicitamente ou buscadas novamente
    except KeyboardInterrupt:
        print("\nExecução da CLI interrompida.")
    except Exception as e:
         # Usar logger configurado se possível
         logger = logging.getLogger(__name__) # Obter logger novamente
         logger.critical(f"Erro fatal não capturado na inicialização da CLI: {e}", exc_info=True)
