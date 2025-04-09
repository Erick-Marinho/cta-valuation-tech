# Remover import asyncpg se ainda existir
# import asyncpg
from fastapi import Depends, Query, Request, HTTPException, status
from typing import Annotated, Dict, Optional, AsyncGenerator
import logging
from functools import lru_cache

# --- Importações SQLAlchemy/SQLModel Async ---
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
# -------------------------------------------

# Importar interfaces e casos de uso
from domain.repositories.document_repository import DocumentRepository
from domain.repositories.chunk_repository import ChunkRepository
from application.use_cases.document_processing.list_documents import ListDocumentsUseCase
from application.use_cases.document_processing.process_document import ProcessDocumentUseCase
from application.interfaces.text_extractor import TextExtractor
from application.interfaces.chunker import Chunker, ChunkQualityEvaluator
from application.interfaces.embedding_provider import EmbeddingProvider
from application.interfaces.llm_provider import LLMProvider
# Importar a implementação concreta do repositório (baseada em asyncpg)
from infrastructure.persistence.sqlmodel.repositories.sm_document_repository import SqlModelDocumentRepository
from infrastructure.persistence.sqlmodel.repositories.sm_chunk_repository import SqlModelChunkRepository
# Importar logger
from application.use_cases.document_processing.get_document_details import GetDocumentDetailsUseCase
from application.use_cases.document_processing.delete_document import DeleteDocumentUseCase

# --- Importar implementações de SERVIÇOS ---
from infrastructure.processors.extractors.pdf_text_extractor import PdfTextExtractor
from infrastructure.processors.chunkers.langchain_chunker import LangchainChunker
from infrastructure.evaluation.chunk_evaluator import BasicChunkQualityEvaluator
from infrastructure.external_services.embedding.huggingface_embedding_provider import HuggingFaceEmbeddingProvider
from infrastructure.llm.providers.nvidia_provider import NvidiaProvider

# Importar o serviço refatorado
from application.services.rag_service import RAGService

# Importar interfaces e implementações de re-ranking
from application.interfaces.reranker import ReRanker
from infrastructure.reranking.cross_encoder_reranker import CrossEncoderReRanker

logger = logging.getLogger(__name__)

# --- Dependência de Sessão Async (sem mudanças) ---
async def get_async_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """ Dependência FastAPI para fornecer uma AsyncSession por requisição. """
    engine: AsyncEngine = request.app.state.db_engine
    if not engine:
         logger.error("AsyncEngine não encontrada no estado da aplicação.")
         raise RuntimeError("Database engine is not available.")
    async_session_factory = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_factory() as session:
        try:
            yield session
        except HTTPException as http_exc: # Capturar HTTPException separadamente
            # Apenas relançar exceções HTTP, não fazer rollback ou logar como erro interno
            raise http_exc
        except Exception as e: # Capturar outras exceções (erros de DB, etc.)
             logger.exception("Erro durante a transação da sessão, realizando rollback.")
             await session.rollback()
             # Para erros não-HTTP, levantar 500
             raise HTTPException(status_code=500, detail=f"Erro interno do servidor durante transação: {e}") from e
        # finally: # async with fecha a sessão
        #     pass

SessionDep = Annotated[AsyncSession, Depends(get_async_session)]
# ----------------------------------------

# --- Provedores de Repositório (Ambos Atualizados para SQLModel) ---
def get_document_repository(session: SessionDep) -> DocumentRepository:
    """ Fornece a implementação do repositório de documentos usando SQLModel. """
    return SqlModelDocumentRepository(session=session)

def get_chunk_repository(session: SessionDep) -> ChunkRepository:
    """ Fornece a implementação do repositório de chunks usando SQLModel. """
    return SqlModelChunkRepository(session=session)
# -------------------------------------------------------

# --- Provedores de Serviços ---
def get_text_extractor() -> TextExtractor:
    """ Fornece a implementação concreta do TextExtractor (para PDF). """
    return PdfTextExtractor()

def get_chunker() -> Chunker:
    return LangchainChunker()

@lru_cache()
def get_embedding_provider() -> EmbeddingProvider:
    logger.info("Criando instância singleton do HuggingFaceEmbeddingProvider...")
    return HuggingFaceEmbeddingProvider()

def get_chunk_quality_evaluator() -> Optional[ChunkQualityEvaluator]:
    try:
        return BasicChunkQualityEvaluator()
    except Exception as e:
        logger.warning(f"Não foi possível criar BasicChunkQualityEvaluator: {e}. Avaliação desabilitada.")
        return None

@lru_cache()
def get_llm_provider() -> LLMProvider:
    """ Fornece a implementação do provedor LLM configurado. """
    logger.info("Criando/obtendo instância singleton do NvidiaProvider...")
    # Aqui você poderia ter lógica para escolher o provedor baseado em settings,
    # mas por enquanto, instanciamos diretamente o NvidiaProvider.
    try:
        return NvidiaProvider()
    except Exception as e:
        logger.critical(f"FALHA CRÍTICA ao inicializar LLMProvider: {e}", exc_info=True)
        # Levantar exceção impede a aplicação de iniciar se o LLM não puder ser configurado
        raise RuntimeError(f"Não foi possível inicializar o LLM Provider: {e}") from e

# --- Provedores de Casos de Uso (sem alterações na assinatura) ---
# Estes agora receberão SqlModelDocumentRepository automaticamente via get_document_repository
def get_list_documents_use_case(
    repo: Annotated[DocumentRepository, Depends(get_document_repository)]
) -> ListDocumentsUseCase:
    return ListDocumentsUseCase(document_repository=repo)

def get_process_document_use_case(
    doc_repo: Annotated[DocumentRepository, Depends(get_document_repository)],
    chunk_repo: Annotated[ChunkRepository, Depends(get_chunk_repository)],
    extractor: Annotated[TextExtractor, Depends(get_text_extractor)],
    chunker: Annotated[Chunker, Depends(get_chunker)],
    embedder: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
    evaluator: Annotated[Optional[ChunkQualityEvaluator], Depends(get_chunk_quality_evaluator)]
) -> ProcessDocumentUseCase:
    return ProcessDocumentUseCase(
        document_repository=doc_repo,
        chunk_repository=chunk_repo,
        text_extractor=extractor,
        chunker=chunker,
        embedding_provider=embedder,
        chunk_evaluator=evaluator
    )

def get_get_document_details_use_case(
    repo: Annotated[DocumentRepository, Depends(get_document_repository)]
) -> GetDocumentDetailsUseCase:
    return GetDocumentDetailsUseCase(document_repository=repo)

def get_delete_document_use_case(
    doc_repo: Annotated[DocumentRepository, Depends(get_document_repository)],
    chunk_repo: Annotated[ChunkRepository, Depends(get_chunk_repository)],
) -> DeleteDocumentUseCase:
    return DeleteDocumentUseCase(
        document_repository=doc_repo,
        chunk_repository=chunk_repo
    )

# --- NOVO: Provedor para ReRanker ---
@lru_cache() # Cache para carregar o modelo CrossEncoder apenas uma vez
def get_reranker() -> ReRanker:
    """ Fornece a implementação do serviço de re-ranking. """
    logger.info("Criando/obtendo instância singleton do CrossEncoderReRanker...")
    try:
        # Pode adicionar lógica para escolher o modelo/device via settings aqui
        return CrossEncoderReRanker()
    except Exception as e:
        logger.critical(f"FALHA CRÍTICA ao inicializar ReRanker: {e}", exc_info=True)
        raise RuntimeError(f"Não foi possível inicializar o ReRanker: {e}") from e

# --- Provedor para o Serviço de Aplicação RAG (MODIFICADO) ---
def get_rag_service(
    embedding_provider: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
    llm_provider: Annotated[LLMProvider, Depends(get_llm_provider)],
    chunk_repo: Annotated[ChunkRepository, Depends(get_chunk_repository)],
    reranker: Annotated[ReRanker, Depends(get_reranker)], # <-- Injetar ReRanker
) -> RAGService:
    """ Fornece a instância do serviço de aplicação RAG. """
    return RAGService(
        embedding_provider=embedding_provider,
        llm_provider=llm_provider,
        chunk_repository=chunk_repo,
        reranker=reranker, # <-- Passar reranker para o construtor
    )

# --- Provedores de Casos de Uso ---
# Se algum endpoint da API precisar chamar o RAGService diretamente,
# ele pode depender de get_rag_service.
# Ex: em api/endpoints/chat.py:
# @router.post("/query")
# async def process_chat_query(
#     request: ChatRequest,
#     rag_service: Annotated[RAGService, Depends(get_rag_service)]
# ):
#     result = await rag_service.process_query(request.query)
#     return result

# --- Parâmetros Comuns de Consulta (sem alterações) ---
async def common_query_parameters(
    limit: int = Query(10, ge=1, le=100, description="Número máximo de itens por página"),
    offset: int = Query(0, ge=0, description="Número de itens a pular"),
    sort_by: Optional[str] = Query("upload_date", description="Campo para ordenação (name, upload_date, size_kb)"),
    order: Optional[str] = Query("desc", description="Ordem da ordenação (asc, desc)")
) -> Dict:
    """
    Define e valida parâmetros comuns de paginação e ordenação.
    """
    # Adicionar validação se necessário (ex: sort_by, order)
    valid_sort_fields = ["name", "upload_date", "size_kb"]
    if sort_by and sort_by not in valid_sort_fields:
        # Poderia lançar HTTPException aqui ou retornar um valor padrão
        sort_by = "upload_date"
    valid_order_values = ["asc", "desc"]
    if order and order.lower() not in valid_order_values:
        order = "desc"

    return {"limit": limit, "offset": offset, "sort_by": sort_by, "order": order.lower()}

# --- Outras dependências (sem alterações) ---

# Exemplo: validate_api_key (sem alterações necessárias para asyncpg)
async def validate_api_key():
    # Implemente sua lógica de validação de chave de API
    # print("WARN: validate_api_key needs implementation!")
    pass # Placeholder

# --- verify_db_health (Adaptado para SessionDep) ---
async def verify_db_health(session: SessionDep):
    """ Verifica a saúde do DB usando a sessão SQLAlchemy. """
    try:
        # Await na execução da query
        result = await session.execute(text("SELECT 1"))
        # Chamar scalar_one() SEM await no objeto result
        scalar_result = result.scalar_one() # <-- CORREÇÃO AQUI (Remover await)
        if scalar_result != 1:
             raise ConnectionError("DB health check failed: Unexpected query result.")
        # logger.debug("DB health check successful (SQLAlchemy).")
    except Exception as e:
        logger.error(f"DB health check failed (SQLAlchemy): {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database service is unavailable.")
# ------------------------------------------

# Adicione outras dependências conforme necessário...
