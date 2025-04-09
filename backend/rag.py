#!/usr/bin/env python
"""
Ferramenta de linha de comando para migração e teste de documentos.

Este script permite importar documentos para o banco de dados e testar buscas,
utilizando a arquitetura modular da aplicação, com instrumentação OpenTelemetry.
"""
import os
import argparse
import logging
import asyncio
import dotenv
from os import listdir
from os.path import isfile, join, isdir
from typing import Dict, Any

# --- Imports da Nova Estrutura ---
from config.config import get_settings, Settings
from utils.logging import configure_logging
# Importar Telemetria
from utils.telemetry import initialize_telemetry, get_tracer
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

# Importar Interfaces, Repositórios, Providers e Use Cases necessários
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from domain.repositories.document_repository import DocumentRepository
from domain.repositories.chunk_repository import ChunkRepository
from application.interfaces.text_extractor import TextExtractor
from application.interfaces.chunker import Chunker, ChunkQualityEvaluator
from application.interfaces.embedding_provider import EmbeddingProvider
from application.interfaces.reranker import ReRanker
from application.interfaces.llm_provider import LLMProvider

# Importar Implementações Concretas
from infrastructure.persistence.sqlmodel.repositories.sm_document_repository import SqlModelDocumentRepository
from infrastructure.persistence.sqlmodel.repositories.sm_chunk_repository import SqlModelChunkRepository
from infrastructure.processors.extractors.pdf_text_extractor import PdfTextExtractor
from infrastructure.processors.chunkers.langchain_chunker import LangchainChunker # Ou SimpleChunker
from infrastructure.evaluation.chunk_evaluator import BasicChunkQualityEvaluator # Ou None
from infrastructure.external_services.embedding.huggingface_embedding_provider import HuggingFaceEmbeddingProvider
from infrastructure.reranking.cross_encoder_reranker import CrossEncoderReRanker
from infrastructure.llm.providers.nvidia_provider import NvidiaProvider

# Importar Use Cases / Serviços de Aplicação
from application.use_cases.document_processing.process_document import ProcessDocumentUseCase
from application.services.rag_service import RAGService
# --- Fim Imports ---

# Carregar variáveis de ambiente
dotenv.load_dotenv()

# Configurar logging e telemetria
configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings() # Carregar settings globalmente
# --- Inicializar Telemetria ---
# Usar nome diferente para distinguir traces do script e da API
initialize_telemetry(service_name=settings.OTEL_SERVICE_NAME + "-script-rag")
# -----------------------------

def lista_arquivos(dir_path):
    """Listar todos os arquivos em um diretório e seus subdiretórios."""
    arquivos_list = []
    try:
        for item in listdir(dir_path):
            item_path = join(dir_path, item)
            if isfile(item_path):
                arquivos_list.append(item_path)
            elif isdir(item_path):
                arquivos_list += lista_arquivos(item_path)
    except FileNotFoundError:
        logger.error(f"Diretório não encontrado: {dir_path}")
    return arquivos_list

# --- Instanciação Manual de Dependências ---

# Cache simples para providers (evita recarregar modelos a cada chamada no script)
_provider_cache: Dict[str, Any] = {}

def get_cached_provider(provider_key: str, factory_func):
    """ Obtém ou cria uma instância de provider do cache. """
    tracer = get_tracer(__name__) # Obter tracer para esta função utilitária
    with tracer.start_as_current_span("get_cached_provider") as span:
        span.set_attribute("provider.key", provider_key)
        if provider_key not in _provider_cache:
            span.set_attribute("provider.cache_hit", False)
            logger.info(f"Criando instância para provider: {provider_key}")
            try:
                 _provider_cache[provider_key] = factory_func()
                 span.set_status(Status(StatusCode.OK))
            except Exception as e:
                 logger.error(f"Erro ao criar instância do provider {provider_key}: {e}", exc_info=True)
                 span.record_exception(e)
                 span.set_status(Status(StatusCode.ERROR, "Falha ao criar instância do provider"))
                 raise # Relança a exceção para quem chamou
        else:
            span.set_attribute("provider.cache_hit", True)
            span.set_status(Status(StatusCode.OK))
        return _provider_cache[provider_key]

async def create_dependencies_for_migration(settings: Settings, session: AsyncSession) -> Dict[str, Any]:
    """ Cria dependências necessárias para o comando 'migrate'. """
    tracer = get_tracer(__name__)
    with tracer.start_as_current_span("create_dependencies_for_migration") as span:
        try:
            # Instanciar providers
            embedding_provider = get_cached_provider("embedding", HuggingFaceEmbeddingProvider)
            text_extractor = PdfTextExtractor()
            chunker = LangchainChunker()
            evaluator = BasicChunkQualityEvaluator()

            # Instanciar repositórios
            doc_repo = SqlModelDocumentRepository(session=session)
            chunk_repo = SqlModelChunkRepository(session=session)

            # Instanciar o Use Case
            process_doc_use_case = ProcessDocumentUseCase(
                document_repository=doc_repo,
                chunk_repository=chunk_repo,
                text_extractor=text_extractor,
                chunker=chunker,
                embedding_provider=embedding_provider,
                chunk_evaluator=evaluator
            )
            span.set_status(Status(StatusCode.OK))
            return {"process_doc_use_case": process_doc_use_case}
        except Exception as e:
            logger.error(f"Erro ao criar dependências de migração: {e}", exc_info=True)
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, "Falha ao criar dependências de migração"))
            raise # Relança para a função chamadora saber

async def create_dependencies_for_search(settings: Settings, session: AsyncSession) -> Dict[str, Any]:
    """ Cria dependências necessárias para o comando 'search'. """
    tracer = get_tracer(__name__)
    with tracer.start_as_current_span("create_dependencies_for_search") as span:
        try:
            # Instanciar providers
            embedding_provider = get_cached_provider("embedding", HuggingFaceEmbeddingProvider)
            llm_provider = get_cached_provider("llm", NvidiaProvider)
            reranker = get_cached_provider("reranker", CrossEncoderReRanker)

            # Instanciar repositório
            chunk_repo = SqlModelChunkRepository(session=session)

            # Instanciar o RAG Service
            rag_service = RAGService(
                embedding_provider=embedding_provider,
                llm_provider=llm_provider,
                chunk_repository=chunk_repo,
                reranker=reranker
            )
            span.set_status(Status(StatusCode.OK))
            return {"rag_service": rag_service}
        except Exception as e:
            logger.error(f"Erro ao criar dependências de busca: {e}", exc_info=True)
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, "Falha ao criar dependências de busca"))
            raise # Relança

# --- Fim Instanciação Manual ---


async def migrar_documentos(settings: Settings, dir_documentos: str):
    """Migra documentos da pasta usando a nova arquitetura."""
    tracer = get_tracer(__name__)
    with tracer.start_as_current_span("rag_script.migrar_documentos") as span:
        span.set_attribute("script.command", "migrate")
        span.set_attribute("script.input_directory", dir_documentos)
        logger.info(f"Iniciando migração de documentos da pasta: {dir_documentos}")

        engine = None # Inicializar engine como None
        try:
            engine = create_async_engine(settings.DATABASE_URL, echo=False)
            AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
            logger.info("Engine e SessionFactory criados.")
            span.set_attribute("db.setup_successful", True)
        except Exception as e:
            logger.error(f"Erro ao criar engine/session factory: {e}", exc_info=True)
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, "Falha ao inicializar DB connection"))
            span.set_attribute("db.setup_successful", False)
            if engine: await engine.dispose() # Tentar limpar se engine foi criado
            return

        arquivos = lista_arquivos(dir_documentos)
        span.set_attribute("script.files_found", len(arquivos))
        logger.info(f"Encontrados {len(arquivos)} arquivos em {dir_documentos}")
        if not arquivos:
            logger.warning("Nenhum arquivo encontrado para migração")
            span.set_attribute("script.files_processed", 0)
            span.set_attribute("script.files_error", 0)
            span.set_status(Status(StatusCode.OK, "No files found"))
            await engine.dispose()
            return

        processed_count = 0
        error_count = 0
        try: # Bloco try para o contexto da sessão
            async with AsyncSessionFactory() as session:
                # Span para criação de dependências
                with tracer.start_as_current_span("rag_script.create_migration_dependencies") as dep_span:
                    try:
                        deps = await create_dependencies_for_migration(settings, session)
                        process_doc_use_case: ProcessDocumentUseCase = deps['process_doc_use_case']
                        dep_span.set_status(Status(StatusCode.OK))
                    except Exception as dep_exc:
                        logger.error(f"Erro crítico durante a criação de dependências: {dep_exc}", exc_info=True)
                        dep_span.record_exception(dep_exc)
                        dep_span.set_status(Status(StatusCode.ERROR, "Falha ao criar dependências"))
                        span.record_exception(dep_exc) # Registrar no span pai também
                        span.set_status(Status(StatusCode.ERROR, "Falha ao criar dependências"))
                        await session.rollback() # Rollback se falhar aqui
                        raise # Re-lança para sair do bloco da sessão

                # Loop de processamento de arquivos
                for arquivo_idx, arquivo in enumerate(arquivos):
                    # Span para cada arquivo
                    with tracer.start_as_current_span(f"rag_script.process_file.{arquivo_idx}") as file_span:
                        nome_arquivo = os.path.basename(arquivo)
                        file_span.set_attribute("file.name", nome_arquivo)
                        file_span.set_attribute("file.path", arquivo)
                        logger.info(f"Processando [{arquivo_idx+1}/{len(arquivos)}]: {nome_arquivo}...")
                        try:
                            tipo_arquivo = os.path.splitext(arquivo)[1][1:].lower()
                            file_span.set_attribute("file.type", tipo_arquivo)
                            if tipo_arquivo != "pdf":
                                logger.warning(f"Pulando arquivo {nome_arquivo}: tipo não suportado ({tipo_arquivo})")
                                file_span.set_attribute("file.skipped", True)
                                file_span.set_attribute("file.skip_reason", "unsupported_type")
                                file_span.set_status(Status(StatusCode.OK, "File skipped"))
                                continue

                            with open(arquivo, "rb") as file:
                                conteudo_binario = file.read()
                            file_span.set_attribute("file.size_bytes", len(conteudo_binario))

                            # Executar o Use Case (pode ter spans internos)
                            documento_processado = await process_doc_use_case.execute(
                                file_name=nome_arquivo,
                                file_content=conteudo_binario,
                                file_type=tipo_arquivo,
                                metadata={"path": arquivo, "origem": "importacao_em_lote_script"},
                            )
                            if documento_processado:
                                logger.info(f"Documento {nome_arquivo} processado com sucesso. ID: {documento_processado.id}")
                                processed_count += 1
                                file_span.set_attribute("file.processed_doc_id", documento_processado.id)
                                file_span.set_status(Status(StatusCode.OK))
                            else:
                                logger.error(f"Processamento de {nome_arquivo} retornou None sem exceção.")
                                error_count += 1
                                file_span.set_status(Status(StatusCode.ERROR, "Processing returned None"))

                        except Exception as e:
                            logger.error(f"Erro ao processar arquivo {nome_arquivo}: {e}", exc_info=True)
                            error_count += 1
                            file_span.record_exception(e)
                            file_span.set_status(Status(StatusCode.ERROR, "Exception during processing"))
                            # Não fazemos rollback aqui, pois o erro é por arquivo.
                            # A transação principal pode continuar para outros arquivos.

        except Exception as session_or_dep_exc:
             logger.error(f"Erro não recuperável no processamento em lote: {session_or_dep_exc}", exc_info=True)
             span.record_exception(session_or_dep_exc)
             span.set_status(Status(StatusCode.ERROR, "Erro irrecuperável no bloco da sessão"))
             # A sessão já foi encerrada ou está em estado de erro

        span.set_attribute("script.files_processed", processed_count)
        span.set_attribute("script.files_error", error_count)
        logger.info(f"Migração concluída. {processed_count} arquivos processados, {error_count} erros.")
        if error_count > 0:
             final_status = Status(StatusCode.ERROR, f"{error_count} errors during migration")
        else:
             final_status = Status(StatusCode.OK)
        span.set_status(final_status)

    # Garantir que o engine seja fechado
    if engine: await engine.dispose()


async def testar_busca(settings: Settings, query: str):
    """Testa a busca RAG usando a nova arquitetura."""
    tracer = get_tracer(__name__)
    with tracer.start_as_current_span("rag_script.testar_busca") as span:
        span.set_attribute("script.command", "search")
        span.set_attribute("script.query", query)
        logger.info(f"Testando busca para: '{query}'")

        engine = None
        try:
            engine = create_async_engine(settings.DATABASE_URL, echo=False)
            AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
            span.set_attribute("db.setup_successful", True)
        except Exception as e:
            logger.error(f"Erro ao criar engine/session factory: {e}", exc_info=True)
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, "Falha ao inicializar DB connection"))
            span.set_attribute("db.setup_successful", False)
            if engine: await engine.dispose()
            return

        result = {}
        try: # Bloco para sessão
            async with AsyncSessionFactory() as session:
                with tracer.start_as_current_span("rag_script.create_search_dependencies") as dep_span:
                    try:
                        deps = await create_dependencies_for_search(settings, session)
                        rag_service: RAGService = deps['rag_service']
                        dep_span.set_status(Status(StatusCode.OK))
                    except Exception as dep_exc:
                        logger.error(f"Erro crítico durante a criação de dependências: {dep_exc}", exc_info=True)
                        dep_span.record_exception(dep_exc)
                        dep_span.set_status(Status(StatusCode.ERROR, "Falha ao criar dependências"))
                        span.record_exception(dep_exc)
                        span.set_status(Status(StatusCode.ERROR, "Falha ao criar dependências"))
                        await session.rollback()
                        raise # Re-lança para sair do bloco da sessão

                try:
                    # A chamada a rag_service.process_query já cria seus próprios spans internos
                    result = await rag_service.process_query(query=query, include_debug_info=True)
                    span.set_attribute("rag.response_received", True)
                    span.set_status(Status(StatusCode.OK)) # Marcar OK se a busca funcionou

                except Exception as e:
                    logger.error(f"Erro ao executar RAGService.process_query: {e}", exc_info=True)
                    result = {"response": f"Erro durante a busca: {e}"}
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, "Exception during RAG query"))
                    span.set_attribute("rag.response_received", False)
                    # Não precisa de rollback aqui, a consulta é apenas leitura

        except Exception as session_or_dep_exc:
             logger.error(f"Erro não recuperável no bloco da sessão/dependências: {session_or_dep_exc}", exc_info=True)
             span.record_exception(session_or_dep_exc)
             span.set_status(Status(StatusCode.ERROR, "Erro irrecuperável no bloco da sessão"))
             result = {"response": f"Erro crítico: {session_or_dep_exc}"}


        # Exibir resultado
        response_str = result.get("response", "Sem resposta ou erro.")
        logger.info(f"Resposta gerada em {result.get('processing_time', 0):.2f} segundos:")
        print("\n" + "=" * 80)
        print(response_str)
        print("=" * 80 + "\n")

        # Exibir informações de debug, se disponíveis
        if "debug_info" in result:
             debug = result["debug_info"]
             logger.info(f"Resultados encontrados (debug): {debug.get('num_results', 'N/A')}")
             if "final_chunk_details" in debug:
                  logger.info("Detalhes dos chunks finais:")
                  for detail in debug["final_chunk_details"]:
                      score_info = f"Score RRF: {detail.get('score_rrf', 'N/A'):.4f}" if isinstance(detail.get('score_rrf'), float) else "Score: N/A"
                      logger.info(f"  - ID: {detail.get('id')}, Doc: {detail.get('doc_id')}, Rank: {detail.get('final_rank')}, {score_info}")

    # Garantir que o engine seja fechado
    if engine: await engine.dispose()

async def main():
    """Função principal do script."""
    # Obter tracer para o main
    tracer = get_tracer(__name__)
    with tracer.start_as_current_span("rag_script.main") as main_span:
        parser = argparse.ArgumentParser( description="Ferramenta para migração de documentos e testes de busca" )
        subparsers = parser.add_subparsers(dest="comando", help="Comandos disponíveis", required=True)

        migrate_parser = subparsers.add_parser( "migrate", help="Migrar documentos para o banco de dados" )
        migrate_parser.add_argument( "--dir", type=str, default="documents", help="Diretório de documentos" )

        search_parser = subparsers.add_parser("search", help="Testar busca RAG")
        search_parser.add_argument( "query", type=str, nargs="?", default="O que é repartição de benefícios?", help="Consulta para teste", )

        args = parser.parse_args()
        main_span.set_attribute("script.command_selected", args.comando)

        # settings já carregado globalmente

        try:
            if args.comando == "migrate":
                main_span.set_attribute("script.migrate_dir", args.dir)
                await migrar_documentos(settings, args.dir)
            elif args.comando == "search":
                main_span.set_attribute("script.search_query", args.query)
                await testar_busca(settings, args.query)
            main_span.set_status(Status(StatusCode.OK)) # Marcar OK se chegou aqui sem erro fatal
        except Exception as main_exc:
             logger.error(f"Erro na execução do comando {args.comando}: {main_exc}", exc_info=True)
             main_span.record_exception(main_exc)
             main_span.set_status(Status(StatusCode.ERROR, "Erro na execução do comando principal"))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExecução interrompida.")
    except Exception as e:
         # Este bloco só captura erros fora do asyncio.run(main())
         logger.critical(f"Erro fatal não capturado: {e}", exc_info=True)
