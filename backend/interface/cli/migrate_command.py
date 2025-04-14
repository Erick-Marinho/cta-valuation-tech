import os
import logging
import asyncio
import dotenv
from os import listdir
from os.path import isfile, join, isdir
from typing import Dict, Any, Optional, List # Adicionado Optional, List

# --- Imports da Nova Estrutura ---
# Ajustar caminhos relativos se necessário, mas assumindo execução a partir da raiz do projeto
# ou PYTHONPATH configurado.
from config.config import get_settings, Settings
# from utils.logging import configure_logging # Configuração de logging pode ser centralizada
from infrastructure.telemetry.opentelemetry import get_tracer # <-- Corrigido
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from utils.filesystem_utils import lista_arquivos

# Importar Interfaces, Repositórios, Providers e Use Cases necessários
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from domain.repositories.document_repository import DocumentRepository
from domain.repositories.chunk_repository import ChunkRepository
from application.interfaces.text_extractor import TextExtractor
from application.interfaces.chunker import Chunker
from application.interfaces.embedding_provider import EmbeddingProvider
# from application.interfaces.reranker import ReRanker # Não usado na migração
# from application.interfaces.llm_provider import LLMProvider # Não usado na migração

# Importar Implementações Concretas
from infrastructure.persistence.sqlmodel.repositories.sm_document_repository import SqlModelDocumentRepository
from infrastructure.persistence.sqlmodel.repositories.sm_chunk_repository import SqlModelChunkRepository
from infrastructure.processors.extractors.pdf_text_extractor import PdfTextExtractor
from infrastructure.processors.chunkers.sentence_chunker import SentenceChunker
# from infrastructure.evaluation.chunk_evaluator import BasicChunkQualityEvaluator # Ou None
from infrastructure.external_services.embedding.huggingface_embedding_provider import HuggingFaceEmbeddingProvider
# from infrastructure.reranking.cross_encoder_reranker import CrossEncoderReRanker # Não usado na migração
# from infrastructure.llm.providers.nvidia_provider import NvidiaProvider # Não usado na migração

# Importar Use Cases / Serviços de Aplicação
from application.use_cases.document_processing.process_document import ProcessDocumentUseCase
# from application.services.rag_service import RAGService # Não usado na migração
# --- Fim Imports ---

logger = logging.getLogger(__name__)

# --- Funções Utilitárias (Considerar mover para utils/ se usadas em outros lugares) ---

_provider_cache: Dict[str, Any] = {} # Manter cache simples para o script

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

# --- Função de Criação de Dependências Específica da Migração ---

async def create_dependencies_for_migration(settings: Settings, session: AsyncSession) -> Dict[str, Any]:
    """ Cria dependências necessárias para o comando 'migrate'. """
    tracer = get_tracer(__name__)
    with tracer.start_as_current_span("create_dependencies_for_migration") as span:
        try:
            # Instanciar providers
            embedding_provider = get_cached_provider("embedding", HuggingFaceEmbeddingProvider)
            text_extractor = PdfTextExtractor()
            chunker = SentenceChunker()

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
            )
            span.set_status(Status(StatusCode.OK))
            return {"process_doc_use_case": process_doc_use_case}
        except Exception as e:
            logger.error(f"Erro ao criar dependências de migração: {e}", exc_info=True)
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, "Falha ao criar dependências de migração"))
            raise # Relança para a função chamadora saber

# --- Função Principal do Comando 'migrate' ---

async def migrar_documentos(settings: Settings, dir_documentos: str):
    """Migra documentos da pasta usando a nova arquitetura."""
    # NOTA: A inicialização de Telemetria e Logging idealmente ocorreria
    # no ponto de entrada (__main__ em main_cli.py) antes de chamar esta função.
    tracer = get_tracer(__name__)
    engine = None  # Inicializar engine como None
    
    try:
        with tracer.start_as_current_span("cli.command.migrate") as span:
            span.set_attribute("command.name", "migrate")
            span.set_attribute("input.directory", dir_documentos)
            logger.info(f"Iniciando migração de documentos da pasta: {dir_documentos}")

            try:
                # --- ADICIONAR PRINT PARA DEBUG ---
                print(f"DEBUG: Tentando criar engine com URL: {settings.DATABASE_URL}")
                # ---------------------------------
                engine = create_async_engine(settings.DATABASE_URL, echo=False)
                AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
                logger.info("Engine e SessionFactory criados para migração.")
                span.set_attribute("db.setup_successful", True)
            except Exception as e:
                logger.error(f"Erro ao criar engine/session factory para migração: {e}", exc_info=True)
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, "Falha ao inicializar DB connection"))
                span.set_attribute("db.setup_successful", False)
                return  # Sair se não conseguir conectar ao DB

            arquivos = lista_arquivos(dir_documentos)
            span.set_attribute("files.found", len(arquivos))
            logger.info(f"Encontrados {len(arquivos)} arquivos em {dir_documentos}")
            if not arquivos:
                logger.warning("Nenhum arquivo encontrado para migração")
                span.set_attribute("files.processed", 0)
                span.set_attribute("files.error", 0)
                span.set_status(Status(StatusCode.OK, "No files found"))
                return

            processed_count = 0
            error_count = 0
            try:  # Bloco try para o contexto da sessão
                async with AsyncSessionFactory() as session:
                    # Span para criação de dependências
                    with tracer.start_as_current_span("cli.create_migration_dependencies") as dep_span:
                        try:
                            deps = await create_dependencies_for_migration(settings, session)
                            process_doc_use_case: ProcessDocumentUseCase = deps['process_doc_use_case']
                            dep_span.set_status(Status(StatusCode.OK))
                        except Exception as dep_exc:
                            logger.error(f"Erro crítico durante a criação de dependências de migração: {dep_exc}", exc_info=True)
                            dep_span.record_exception(dep_exc)
                            dep_span.set_status(Status(StatusCode.ERROR, "Falha ao criar dependências"))
                            span.record_exception(dep_exc) # Registrar no span pai também
                            span.set_status(Status(StatusCode.ERROR, "Falha ao criar dependências"))
                            await session.rollback() # Rollback se falhar aqui
                            raise # Re-lança para sair do bloco da sessão

                    # Loop de processamento de arquivos
                    for arquivo_idx, arquivo in enumerate(arquivos):
                        # Span para cada arquivo
                        with tracer.start_as_current_span(f"cli.process_file.{arquivo_idx}") as file_span:
                            nome_arquivo = os.path.basename(arquivo)
                            file_span.set_attribute("file.name", nome_arquivo)
                            file_span.set_attribute("file.path", arquivo)
                            logger.info(f"Processando [{arquivo_idx+1}/{len(arquivos)}]: {nome_arquivo}...")
                            try:
                                tipo_arquivo = os.path.splitext(arquivo)[1][1:].lower()
                                file_span.set_attribute("file.type", tipo_arquivo)
                                if tipo_arquivo != "pdf": # Exemplo: só processa PDF neste script
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
                                    metadata={"path": arquivo, "origem": "cli_migration"}, # Metadados de origem
                                )
                                if documento_processado and documento_processado.id is not None:
                                    logger.info(f"Documento {nome_arquivo} processado com sucesso. ID: {documento_processado.id}")
                                    processed_count += 1
                                    file_span.set_attribute("file.processed_doc_id", documento_processado.id)
                                    file_span.set_status(Status(StatusCode.OK))
                                else:
                                    logger.error(f"Processamento de {nome_arquivo} não retornou documento válido ou ID.")
                                    error_count += 1
                                    file_span.set_status(Status(StatusCode.ERROR, "Processing returned invalid document or ID"))

                            except Exception as e:
                                logger.error(f"Erro ao processar arquivo {nome_arquivo}: {e}", exc_info=True)
                                error_count += 1
                                file_span.record_exception(e)
                                file_span.set_status(Status(StatusCode.ERROR, "Exception during file processing"))
                                # Não fazemos rollback aqui, pois o erro é por arquivo.

            except Exception as session_or_dep_exc:
                logger.error(f"Erro não recuperável no processamento em lote da migração: {session_or_dep_exc}", exc_info=True)
                span.record_exception(session_or_dep_exc)
                span.set_status(Status(StatusCode.ERROR, "Erro irrecuperável no bloco da sessão de migração"))
                # A sessão já foi encerrada ou está em estado de erro

            span.set_attribute("files.processed_count", processed_count)
            span.set_attribute("files.error_count", error_count)
            logger.info(f"Migração concluída. {processed_count} arquivos processados, {error_count} erros.")
            if error_count > 0:
                final_status = Status(StatusCode.ERROR, f"{error_count} errors during migration")
            else:
                final_status = Status(StatusCode.OK)
            span.set_status(final_status)
            
    finally:
        # Garantir que o engine seja fechado
        if engine:
            await engine.dispose()
            logger.info("Engine de migração finalizado.")
