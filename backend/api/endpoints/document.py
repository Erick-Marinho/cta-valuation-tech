"""
Endpoints para gerenciamento de documentos.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Path, status
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging
from core.services.document_service import get_document_service, DocumentService
from core.models.document import Document
from core.config import get_settings, Settings
from ..dependencies import validate_api_key, verify_db_health, common_query_parameters

logger = logging.getLogger(__name__)

# Models de dados para requisições e respostas
class DocumentResponse(BaseModel):
    """Model para resposta com informações de documento."""
    id: int
    name: str
    file_type: str
    upload_date: str
    size_kb: float
    chunks_count: int
    processed: bool
    metadata: Dict[str, Any]

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

@router.get("/", response_model=DocumentListResponse, dependencies=[Depends(verify_db_health)])
async def list_documents(
    document_service: DocumentService = Depends(get_document_service),
    settings: Settings = Depends(get_settings),
    params: Dict = Depends(common_query_parameters),
    name_filter: Optional[str] = Query(None, description="Filtrar por nome do documento")
):
    """
    Lista todos os documentos disponíveis.
    
    Args:
        params: Parâmetros de consulta (limit, offset, sort_by, order)
        name_filter: Filtro opcional por nome do documento
        
    Returns:
        DocumentListResponse: Lista de documentos
    """
    try:
        # Obter documentos (sem conteúdo binário)
        all_documents = await document_service.list_documents(include_content=False)
        
        # Aplicar filtro por nome, se fornecido
        if name_filter:
            filtered_documents = [doc for doc in all_documents if name_filter.lower() in doc.name.lower()]
        else:
            filtered_documents = all_documents
        
        # Aplicar ordenação
        sort_field = params.get("sort_by", "upload_date")
        if sort_field == "name":
            filtered_documents.sort(key=lambda x: x.name)
        elif sort_field == "upload_date":
            filtered_documents.sort(key=lambda x: x.upload_date)
        elif sort_field == "size_kb":
            filtered_documents.sort(key=lambda x: x.size_kb)
        
        # Inverter se ordem for descendente
        if params.get("order", "asc").lower() == "desc":
            filtered_documents.reverse()
        
        # Aplicar paginação
        limit = params.get("limit", 10)
        offset = params.get("offset", 0)
        paginated_documents = filtered_documents[offset:offset + limit]
        
        # Converter para formato de resposta
        document_responses = [
            DocumentResponse(
                id=doc.id,
                name=doc.name,
                file_type=doc.file_type,
                upload_date=doc.upload_date.isoformat(),
                size_kb=doc.size_kb,
                chunks_count=doc.chunks_count,
                processed=doc.processed,
                metadata=doc.metadata
            )
            for doc in paginated_documents
        ]
        
        return DocumentListResponse(
            documents=document_responses,
            total=len(filtered_documents),
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(f"Erro ao listar documentos: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar documentos: {str(e)}")

@router.post("/upload", response_model=DocumentUploadResponse, 
             #dependencies=[Depends(validate_api_key), Depends(verify_db_health)]
                           )
async def upload_document(
    file: UploadFile = File(...),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Faz upload e processa um novo documento.
    
    Args:
        file: Arquivo a ser processado
        
    Returns:
        DocumentUploadResponse: Informações sobre o documento processado
    """
    try:
        # Validar tipo de arquivo
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Apenas arquivos PDF são suportados atualmente"
            )
        
        # Ler conteúdo do arquivo
        file_content = await file.read()
        
        if len(file_content) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Arquivo muito grande. O tamanho máximo é 10MB"
            )
        
        # Processar documento
        document = await document_service.process_document(
            file_name=file.filename,
            file_content=file_content,
            file_type="pdf",
            metadata={"origem": "upload_api"}
        )
        
        # Criar resposta
        return DocumentUploadResponse(
            id=document.id,
            name=document.name,
            file_type=document.file_type,
            size_kb=document.size_kb,
            chunks_count=document.chunks_count,
            processed=document.processed,
            message="Documento processado com sucesso"
        )
        
    except HTTPException:
        # Repassar HTTPExceptions específicas
        raise
    except Exception as e:
        logger.error(f"Erro ao processar upload: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar documento: {str(e)}")

@router.get("/{document_id}", response_model=DocumentResponse, dependencies=[Depends(verify_db_health)])
async def get_document(
    document_id: int = Path(..., description="ID do documento"),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Obtém informações sobre um documento específico.
    
    Args:
        document_id: ID do documento
        
    Returns:
        DocumentResponse: Informações do documento
    """
    try:
        document = await document_service.get_document(document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documento com ID {document_id} não encontrado"
            )
        
        return DocumentResponse(
            id=document.id,
            name=document.name,
            file_type=document.file_type,
            upload_date=document.upload_date.isoformat(),
            size_kb=document.size_kb,
            chunks_count=document.chunks_count,
            processed=document.processed,
            metadata=document.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter documento {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao obter documento: {str(e)}")

@router.delete("/{document_id}", dependencies=[Depends(validate_api_key), Depends(verify_db_health)])
async def delete_document(
    document_id: int = Path(..., description="ID do documento"),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Exclui um documento pelo ID.
    
    Args:
        document_id: ID do documento a ser excluído
        
    Returns:
        dict: Mensagem de confirmação
    """
    try:
        document = await document_service.get_document(document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documento com ID {document_id} não encontrado"
            )
        
        success = await document_service.delete_document(document_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Falha ao excluir documento"
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": f"Documento {document_id} excluído com sucesso"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao excluir documento {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao excluir documento: {str(e)}")