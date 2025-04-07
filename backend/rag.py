#!/usr/bin/env python
"""
Ferramenta de linha de comando para migração e teste de documentos.

Este script permite importar documentos para o banco de dados e testar buscas,
utilizando a arquitetura modular da aplicação.
"""
import os
import argparse
import logging
import asyncio
import dotenv
from os import listdir
from os.path import isfile, join, isdir

# Importar componentes da arquitetura modular
from core.config import get_settings
from core.services.document_service import get_document_service
from core.services.embedding_service import get_embedding_service
from core.services.rag_service import get_rag_service
from db.schema import setup_database, is_database_healthy
from utils.logging import configure_logging

# Carregar variáveis de ambiente
dotenv.load_dotenv()

# Configurar logging
configure_logging()
logger = logging.getLogger(__name__)


def lista_arquivos(dir_path):
    """Listar todos os arquivos em um diretório e seus subdiretórios."""
    arquivos_list = []

    for item in listdir(dir_path):
        item_path = join(dir_path, item)
        if isfile(item_path):
            arquivos_list.append(item_path)
        elif isdir(item_path):
            arquivos_list += lista_arquivos(item_path)
    return arquivos_list


async def migrar_documentos(dir_documentos="documents"):
    """Migra documentos da pasta para o banco de dados."""
    logger.info(f"Iniciando migração de documentos da pasta: {dir_documentos}")

    # Inicializar banco de dados
    setup_database()
    if not is_database_healthy():
        logger.error("Banco de dados não está saudável. Abortando migração.")
        return

    # Obter serviço de documentos
    document_service = get_document_service()

    # Obter lista de arquivos
    arquivos = lista_arquivos(dir_documentos)
    logger.info(f"Encontrados {len(arquivos)} arquivos em {dir_documentos}")

    if not arquivos:
        logger.warning("Nenhum arquivo encontrado para migração")
        return

    # Processar cada arquivo
    for arquivo in arquivos:
        try:
            nome_arquivo = os.path.basename(arquivo)
            tipo_arquivo = os.path.splitext(arquivo)[1][1:].lower()

            # Verificar se é um tipo suportado (PDF)
            if tipo_arquivo != "pdf":
                logger.warning(
                    f"Pulando arquivo {nome_arquivo}: tipo não suportado ({tipo_arquivo})"
                )
                continue

            logger.info(f"Processando: {nome_arquivo}")

            # Ler conteúdo do arquivo
            with open(arquivo, "rb") as file:
                conteudo_binario = file.read()

            # Processar documento usando o serviço modular
            documento = await document_service.process_document(
                file_name=nome_arquivo,
                file_content=conteudo_binario,
                file_type=tipo_arquivo,
                metadata={"path": arquivo, "origem": "importacao_em_lote"},
            )

            logger.info(
                f"Documento {nome_arquivo} processado com sucesso. ID: {documento.id}, Chunks: {documento.chunks_count}"
            )

        except Exception as e:
            logger.error(f"Erro ao processar arquivo {arquivo}: {e}")

    logger.info("Migração concluída!")


async def testar_busca(query="CTA Value Tech"):
    """Testa a busca RAG usando a nova arquitetura."""
    logger.info(f"Testando busca para: '{query}'")

    # Verificar banco de dados
    if not is_database_healthy():
        logger.error("Banco de dados não está saudável. Abortando teste.")
        return

    # Obter serviço RAG
    rag_service = get_rag_service()

    # Realizar busca
    result = await rag_service.process_query(query=query, include_debug_info=True)

    # Exibir resultado
    logger.info(f"Resposta gerada em {result.get('processing_time', 0):.2f} segundos:")
    print("\n" + "=" * 80)
    print(result.get("response", "Sem resposta"))
    print("=" * 80 + "\n")

    # Exibir informações de debug, se disponíveis
    if "debug_info" in result:
        debug = result["debug_info"]
        logger.info(f"Resultados encontrados: {debug.get('num_results', 0)}")

        if "sources" in debug and "scores" in debug:
            for i, (source, score) in enumerate(zip(debug["sources"], debug["scores"])):
                logger.info(f"Resultado {i+1}: {source} (score: {score:.4f})")


async def main():
    """Função principal do script."""
    parser = argparse.ArgumentParser(
        description="Ferramenta para migração de documentos e testes de busca"
    )

    # Definir subcomandos
    subparsers = parser.add_subparsers(dest="comando", help="Comandos disponíveis")

    # Comando de migração
    migrate_parser = subparsers.add_parser(
        "migrate", help="Migrar documentos para o banco de dados"
    )
    migrate_parser.add_argument(
        "--dir", type=str, default="documents", help="Diretório de documentos"
    )

    # Comando de busca
    search_parser = subparsers.add_parser("search", help="Testar busca RAG")
    search_parser.add_argument(
        "query",
        type=str,
        nargs="?",
        default="CTA Value Tech",
        help="Consulta para teste",
    )

    # Parsing dos argumentos
    args = parser.parse_args()

    # Executar comando apropriado
    if args.comando == "migrate":
        await migrar_documentos(args.dir)
    elif args.comando == "search":
        await testar_busca(args.query)
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
