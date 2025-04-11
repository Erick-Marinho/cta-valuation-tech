"""
Endpoints para gerenciamento de documentos.
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Query,
    Path,
    status,
)
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging
from domain.aggregates.document.document import Document
from config.config import get_settings, Settings
from application.use_cases.document_processing.list_documents import ListDocumentsUseCase
from interface.api.dependencies import validate_api_key, verify_db_health, common_query_parameters, get_list_documents_use_case, get_process_document_use_case, get_get_document_details_use_case, get_delete_document_use_case
from application.use_cases.document_processing.process_document import ProcessDocumentUseCase, DocumentProcessingError
from application.use_cases.document_processing.get_document_details import GetDocumentDetailsUseCase
from application.use_cases.document_processing.delete_document import DeleteDocumentUseCase
from application.dtos.document_dto import DocumentDTO

logger = logging.getLogger(__name__)


# Modelos de dados para requisições e respostas
class DocumentResponse(BaseModel):
    """Modelo para resposta com informações de documento."""

    id: int
    name: str
    file_type: Optional[str]
    upload_date: Optional[str]
    size_kb: Optional[float]
    chunks_count: Optional[int]
    processed: Optional[bool]
    metadata: Optional[Dict[str, Any]]


class DocumentListResponse(BaseModel):
    """Modelo para resposta com lista de documentos."""

    documents: List[DocumentResponse]
    total: int
    limit: int
    offset: int


class DocumentUploadResponse(BaseModel):
    """Modelo para resposta de upload de documento."""

    id: int
    name: str
    file_type: str
    size_kb: float
    chunks_count: int
    processed: bool
    message: str


# Roteador para endpoints de documentos
router = APIRouter(prefix="/documents", tags=["documents"])


@router.get(
    "/",
    response_model=DocumentListResponse,
    dependencies=[Depends(verify_db_health)]
)
async def list_documents(
    list_docs_use_case: ListDocumentsUseCase = Depends(get_list_documents_use_case),
    params: Dict = Depends(common_query_parameters),
    name_filter: Optional[str] = Query(
        None, description="Filtrar por nome do documento (case-insensitive)"
    ),
):
    """
    Lista documentos disponíveis com filtros, ordenação e paginação.
    """
    try:
        limit = params["limit"]
        offset = params["offset"]
        sort_by = params["sort_by"]
        order = params["order"]

        document_dtos_page, total_documents = await list_docs_use_case.execute(limit=limit, offset=offset)

        if name_filter:
            filtered_documents_page = [
                dto for dto in document_dtos_page if name_filter.lower() in dto.name.lower()
            ]
        else:
            filtered_documents_page = document_dtos_page

        reverse_sort = order == "desc"
        if sort_by == "name":
            filtered_documents_page.sort(key=lambda x: x.name, reverse=reverse_sort)
        elif sort_by == "upload_date":
            filtered_documents_page.sort(key=lambda x: x.upload_date or datetime.datetime.min, reverse=reverse_sort)
        elif sort_by == "size_kb":
            filtered_documents_page.sort(key=lambda x: x.size_kb or 0.0, reverse=reverse_sort)

        document_responses = [
            DocumentResponse(
                id=dto.id,
                name=dto.name,
                file_type=dto.file_type,
                upload_date=dto.upload_date.isoformat() if dto.upload_date else None,
                size_kb=dto.size_kb,
                chunks_count=dto.chunks_count,
                processed=dto.processed,
                metadata=dto.metadata,
            )
            for dto in filtered_documents_page
        ]

        return DocumentListResponse(
            documents=document_responses,
            total=total_documents,
            limit=limit,
            offset=offset,
        )

    except RuntimeError as rte:
         logger.error(f"Erro de configuração/runtime: {rte}")
         raise HTTPException(
             status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
             detail="Erro de configuração interna ou serviço indisponível."
         )
    except Exception as e:
        logger.exception(f"Erro inesperado ao listar documentos:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar a solicitação de listagem de documentos."
        )


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    dependencies=[Depends(validate_api_key), Depends(verify_db_health)],
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    process_use_case: ProcessDocumentUseCase = Depends(get_process_document_use_case),
    file: UploadFile = File(...),
):
    """
    Faz upload e dispara o processamento de um novo documento.
    """
    MAX_FILE_SIZE = 20 * 1024 * 1024 # Exemplo: 20MB
    if file.size > MAX_FILE_SIZE:
         raise HTTPException(
             status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
             detail=f"Arquivo muito grande. O tamanho máximo é {MAX_FILE_SIZE // (1024*1024)}MB",
         )

    try:
        file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        if file_extension != "pdf":
            logger.warning(f"Recebido upload de arquivo não-PDF: {file.filename}")

        file_content = await file.read()
        if not file_content:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo enviado está vazio.")

        initial_metadata = {"source": "api_upload", "original_filename": file.filename}

        processed_document = await process_use_case.execute(
            file_name=file.filename,
            file_content=file_content,
            file_type=file_extension,
            metadata=initial_metadata,
        )

        original_size_kb = file.size / 1024 if file.size else 0

        return DocumentUploadResponse(
            id=processed_document.id,
            name=processed_document.name,
            file_type=processed_document.file_type,
            size_kb=round(original_size_kb, 2),
            chunks_count=processed_document.chunks_count,
            processed=processed_document.processed,
            message=f"Documento '{processed_document.name}' recebido e processamento iniciado/concluído.",
        )

    except DocumentProcessingError as e:
        logger.error(f"Erro ao processar documento '{file.filename}': {e}")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro inesperado durante o upload do arquivo '{file.filename}':")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno inesperado ao processar o documento."
        )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    dependencies=[Depends(verify_db_health)],
    responses={404: {"description": "Documento não encontrado"}}
)
async def get_document(
    get_details_use_case: GetDocumentDetailsUseCase = Depends(get_get_document_details_use_case),
    document_id: int = Path(..., description="ID do documento a ser buscado", ge=1),
):
    """ Obtém informações detalhadas sobre um documento específico. """
    try:
        document_dto = await get_details_use_case.execute(document_id)

        if document_dto is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documento com ID {document_id} não encontrado.",
            )

        return DocumentResponse(
            id=document_dto.id,
            name=document_dto.name,
            file_type=document_dto.file_type,
            upload_date=document_dto.upload_date.isoformat() if document_dto.upload_date else None,
            size_kb=document_dto.size_kb,
            chunks_count=document_dto.chunks_count,
            processed=document_dto.processed,
            metadata=document_dto.metadata,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro inesperado ao buscar documento ID {document_id}:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno ao buscar detalhes do documento."
        )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(validate_api_key), Depends(verify_db_health)],
    responses={
        500: {"description": "Erro interno ao tentar excluir o documento"}
    }
)
async def delete_document(
    delete_use_case: DeleteDocumentUseCase = Depends(get_delete_document_use_case),
    document_id: int = Path(..., description="ID do documento a ser excluído", ge=1),
):
    """ Exclui um documento e todos os seus chunks associados. """
    try:
        success = await delete_use_case.execute(document_id)

        if not success:
            logger.error(f"O caso de uso DeleteDocumentUseCase retornou False para o ID {document_id}, indicando falha na exclusão.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Não foi possível excluir o documento devido a um erro interno."
            )
        # Se success for True, retorna HTTP 204 No Content automaticamente
        return

    except HTTPException:
         raise
    except Exception as e:
        logger.exception(f"Erro inesperado ao excluir documento ID {document_id}:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno inesperado ao processar a solicitação de exclusão."
        )
