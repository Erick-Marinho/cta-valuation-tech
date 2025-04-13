import logging
import asyncio
from typing import Dict, Any

# --- Imports da Nova Estrutura ---
from config.config import get_settings, Settings
from utils.telemetry import get_tracer # Assumindo que utils está acessível
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

# Importar Interfaces, Repositórios, Providers e Use Cases necessários
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
# from domain.repositories.document_repository import DocumentRepository # Não usado na busca
from domain.repositories.chunk_repository import ChunkRepository
# from application.interfaces.text_extractor import TextExtractor # Não usado na busca
# from application.interfaces.chunker import Chunker, ChunkQualityEvaluator # Não usado na busca
from application.interfaces.embedding_provider import EmbeddingProvider
from application.interfaces.reranker import ReRanker
from application.interfaces.llm_provider import LLMProvider

# Importar Implementações Concretas
# from infrastructure.persistence.sqlmodel.repositories.sm_document_repository import SqlModelDocumentRepository # Não usado
from infrastructure.persistence.sqlmodel.repositories.sm_chunk_repository import SqlModelChunkRepository
# from infrastructure.processors.extractors.pdf_text_extractor import PdfTextExtractor # Não usado
# from infrastructure.processors.chunkers.langchain_chunker import LangchainChunker # Não usado
# from infrastructure.evaluation.chunk_evaluator import BasicChunkQualityEvaluator # Não usado
from infrastructure.external_services.embedding.huggingface_embedding_provider import HuggingFaceEmbeddingProvider
from infrastructure.reranking.cross_encoder_reranker import CrossEncoderReRanker
from infrastructure.llm.providers.nvidia_provider import NvidiaProvider

# Importar Use Cases / Serviços de Aplicação
from application.use_cases.rag.process_query_use_case import ProcessQueryUseCase

# Importar utilitário de cache compartilhado
from .shared import get_cached_provider
# --- Fim Imports ---

logger = logging.getLogger(__name__)

# --- Função de Criação de Dependências Específica da Busca ---

async def create_dependencies_for_search(settings: Settings, session: AsyncSession) -> Dict[str, Any]:
    """ Cria dependências necessárias para o comando 'search'. """
    tracer = get_tracer(__name__)
    with tracer.start_as_current_span("create_dependencies_for_search") as span:
        try:
            # Instanciar providers usando cache
            embedding_provider = get_cached_provider("embedding", HuggingFaceEmbeddingProvider)
            llm_provider = get_cached_provider("llm", NvidiaProvider)
            reranker = get_cached_provider("reranker", CrossEncoderReRanker)

            # Instanciar repositório
            chunk_repo = SqlModelChunkRepository(session=session)

            # Instanciar o Use Case
            process_query_uc = ProcessQueryUseCase(
                 embedding_provider=embedding_provider,
                 llm_provider=llm_provider,
                 chunk_repository=chunk_repo,
                 reranker=reranker
            )
            span.set_status(Status(StatusCode.OK))
            return {"process_query_uc": process_query_uc}
        except Exception as e:
            logger.error(f"Erro ao criar dependências de busca: {e}", exc_info=True)
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, "Falha ao criar dependências de busca"))
            raise # Relança

# --- Função Principal do Comando 'search' ---

async def testar_busca(settings: Settings, query: str):
    """Testa a busca RAG usando a nova arquitetura."""
    tracer = get_tracer(__name__)
    engine = None

    try:
        with tracer.start_as_current_span("cli.command.search") as span:
            span.set_attribute("command.name", "search")
            span.set_attribute("input.query", query)
            logger.info(f"Testando busca para: '{query}'")

            try:
                engine = create_async_engine(settings.DATABASE_URL, echo=False)
                AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
                span.set_attribute("db.setup_successful", True)
            except Exception as e:
                logger.error(f"Erro ao criar engine/session factory para busca: {e}", exc_info=True)
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, "Falha ao inicializar DB connection"))
                span.set_attribute("db.setup_successful", False)
                return

            result = {}
            try:
                async with AsyncSessionFactory() as session:
                    with tracer.start_as_current_span("cli.create_search_dependencies") as dep_span:
                        try:
                            deps = await create_dependencies_for_search(settings, session)
                            process_query_uc: ProcessQueryUseCase = deps['process_query_uc']
                            dep_span.set_status(Status(StatusCode.OK))
                        except Exception as dep_exc:
                            logger.error(f"Erro crítico durante a criação de dependências de busca: {dep_exc}", exc_info=True)
                            dep_span.record_exception(dep_exc)
                            dep_span.set_status(Status(StatusCode.ERROR, "Falha ao criar dependências"))
                            span.record_exception(dep_exc)
                            span.set_status(Status(StatusCode.ERROR, "Falha ao criar dependências"))
                            await session.rollback()
                            raise

                    try:
                        result = await process_query_uc.execute(query=query, include_debug_info=True)
                        span.set_attribute("rag.response_received", True)
                        span.set_status(Status(StatusCode.OK))

                    except Exception as e:
                        logger.error(f"Erro ao executar process_query_uc.execute: {e}", exc_info=True)
                        result = {"response": f"Erro durante a busca: {e}"}
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, "Exception during RAG query"))
                        span.set_attribute("rag.response_received", False)

            except Exception as session_or_dep_exc:
                 logger.error(f"Erro não recuperável no bloco da sessão/dependências da busca: {session_or_dep_exc}", exc_info=True)
                 span.record_exception(session_or_dep_exc)
                 span.set_status(Status(StatusCode.ERROR, "Erro irrecuperável no bloco da sessão de busca"))
                 result = {"response": f"Erro crítico: {session_or_dep_exc}"}

            response_str = result.get("response", "Sem resposta ou erro.")
            processing_time = result.get('processing_time', 0)
            logger.info(f"Resposta gerada em {processing_time:.2f} segundos:")
            print("\n" + "=" * 80)
            print(response_str)
            print("=" * 80 + "\n")

            if "debug_info" in result:
                 debug = result["debug_info"]
                 logger.info(f"Resultados encontrados (debug): {debug.get('num_results', 'N/A')}")
                 if "final_chunk_details" in debug:
                      logger.info("Detalhes dos chunks finais:")
                      for detail in debug["final_chunk_details"]:
                          score_info = f"Score RRF: {detail.get('score_rrf', 'N/A'):.4f}" if isinstance(detail.get('score_rrf'), float) else "Score: N/A"
                          logger.info(f"  - ID: {detail.get('id')}, Doc: {detail.get('doc_id')}, Rank: {detail.get('final_rank')}, {score_info}")

    finally:
        if engine:
            await engine.dispose()
            logger.info("Engine de busca finalizado.")
