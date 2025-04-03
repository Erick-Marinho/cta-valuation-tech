"""
Endpoints para conversação e consultas usando RAG.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from core.services.rag_service import get_rag_service, RAGService
from core.config import get_settings, Settings
from utils.metrics_prometheus import record_user_feedback

# Modelos de dados para requisições e respostas
class ChatQuery(BaseModel):
    """Modelo para consulta de chat."""
    query: str
    document_ids: Optional[List[int]] = None
    

class ChatResponse(BaseModel):
    """Modelo para resposta de chat."""
    response: str
    processing_time: Optional[float] = None
    debug_info: Optional[Dict[str, Any]] = None


class SuggestedQuestion(BaseModel):
    """Modelo para pergunta sugerida."""
    question: str

class FeedbackRequest(BaseModel):
    """Modelo para submissão de feedback."""
    query_id: str
    is_helpful: bool
    comments: Optional[str] = None


# Roteador para endpoints de chat
router = APIRouter(prefix="/chat", tags=["chat"])

# Dependência para obter o serviço RAG
def get_rag_svc() -> RAGService:
    return get_rag_service()

# Dependência para obter configurações
def get_app_settings() -> Settings:
    return get_settings()


@router.post("/", response_model=ChatResponse)
async def process_chat_query(
    query: ChatQuery,
    rag_service: RAGService = Depends(get_rag_svc),
    settings: Settings = Depends(get_app_settings)
):
    """
    Processa uma consulta do usuário usando o sistema RAG.
    
    Args:
        query: Consulta do usuário e opcionalmente IDs de documentos para filtrar
        
    Returns:
        ChatResponse: Resposta gerada pelo sistema
    """
    try:
        # Debug mode ativado nas configurações ou pelo parâmetro debug=true na URL
        include_debug = settings.DEBUG
        
        # Processar a consulta
        result = await rag_service.process_query(
            query=query.query,
            filtro_documentos=query.document_ids,
            include_debug_info=include_debug
        )
        
        return ChatResponse(
            response=result.get("response", ""),
            processing_time=result.get("processing_time"),
            debug_info=result.get("debug_info") if include_debug else None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar consulta: {str(e)}")


@router.get("/suggested-questions", response_model=List[SuggestedQuestion])
async def get_suggested_questions(
    query: Optional[str] = Query(None, description="Consulta para basear as sugestões"),
    limit: int = Query(5, description="Número máximo de sugestões"),
    rag_service: RAGService = Depends(get_rag_svc)
):
    """
    Retorna perguntas sugeridas, opcionalmente baseadas em uma consulta do usuário.
    
    Args:
        query: Consulta opcional para basear as sugestões
        limit: Número máximo de sugestões a retornar
        
    Returns:
        List[SuggestedQuestion]: Lista de perguntas sugeridas
    """
    try:
        if query:
            # Sugestões baseadas na consulta do usuário
            questions = rag_service.get_similar_questions(query, limit=limit)
        else:
            # Sugestões padrão se não houver consulta
            questions = [
                "O que é CTA Value Tech?",
                "Como funciona a valoração de tecnologias?",
                "Quais são os indicadores de sustentabilidade utilizados?",
                "Como são calculados os royalties?",
                "Quais princípios da Convenção sobre a Diversidade Biológica são considerados?"
            ][:limit]
        
        # Converter para o formato de resposta
        return [SuggestedQuestion(question=q) for q in questions]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter sugestões: {str(e)}")
    
@router.post("/feedback", status_code=200)
async def submit_feedback(
    feedback: FeedbackRequest
):
    """
    Submete feedback do usuário sobre uma resposta.
    
    Args:
        feedback: Detalhes do feedback
        
    Returns:
        dict: Confirmação de recebimento
    """
    try:
        # Registrar feedback nas métricas
        rating = "positive" if feedback.is_helpful else "negative"
        record_user_feedback(rating)
        
        # Aqui você pode salvar o feedback em um banco de dados para análise posterior
        # Isso seria importante para melhorias futuras
        
        return {"status": "success", "message": "Feedback recebido com sucesso"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar feedback: {str(e)}")