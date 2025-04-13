"""
Endpoints para conversação e consultas usando RAG.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional, Dict, Any, Annotated
from pydantic import BaseModel
from application.use_cases.rag.process_query_use_case import ProcessQueryUseCase
from interface.api.dependencies import get_process_query_use_case
from config.config import get_settings, Settings
from shared.exceptions import CoreException
from infrastructure.metrics.prometheus.metrics_prometheus import record_user_feedback
import logging

# Adicionar esta linha para obter o logger
logger = logging.getLogger(__name__)

# Modelos de dados para requisições e respostas
class ChatQuery(BaseModel):
    """Modelo para consulta de chat."""

    query: str
    document_ids: Optional[List[int]] = None
    max_results: Optional[int] = None
    include_debug: bool = False


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

    query_id: Optional[str] = None
    is_helpful: bool
    comments: Optional[str] = None


# Roteador para endpoints de chat
router = APIRouter(prefix="/chat", tags=["chat"])


# Dependência para obter configurações
SettingsDep = Annotated[Settings, Depends(get_settings)]

# Dependência para obter o serviço RAG
ProcessQueryUseCaseDep = Annotated[ProcessQueryUseCase, Depends(get_process_query_use_case)]


@router.post("/", response_model=ChatResponse)
async def handle_chat_query(
    request_body: ChatQuery,
    process_query_uc: ProcessQueryUseCaseDep,
    settings: SettingsDep,
):
    """
    Recebe uma consulta do usuário e retorna a resposta gerada pelo RAG.
    """
    logger.info(f"Recebida consulta no endpoint /chat: '{request_body.query[:50]}...'")
    try:
        # Processar a consulta
        result_dict = await process_query_uc.execute(
            query=request_body.query,
            filtro_documentos=request_body.document_ids,
            max_results=request_body.max_results,
            include_debug_info=request_body.include_debug
        )

        return ChatResponse(
            response=result_dict.get("response", "Erro: Resposta não encontrada."),
            processing_time=result_dict.get("processing_time"),
            debug_info=result_dict.get("debug_info"),
        )

    except ValueError as ve:
        logger.error(f"Erro de valor ao processar consulta: {ve}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.exception(f"Erro inesperado no endpoint /chat:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar a consulta."
        )


@router.get("/suggested-questions", response_model=List[SuggestedQuestion])
async def get_suggested_questions(
    query: Optional[str] = Query(None, description="Consulta para basear as sugestões"),
    limit: int = Query(5, description="Número máximo de sugestões"),
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
            questions = [
                "O que é CTA Value Tech?",
                "Como funciona a valoração de tecnologias?",
                "Quais são os indicadores de sustentabilidade utilizados?",
                "Como são calculados os royalties?",
                "Quais princípios da Convenção sobre a Diversidade Biológica são considerados?",
            ][:limit]
        else:
            # Sugestões padrão se não houver consulta
            questions = [
                "O que é CTA Value Tech?",
                "Como funciona a valoração de tecnologias?",
                "Quais são os indicadores de sustentabilidade utilizados?",
                "Como são calculados os royalties?",
                "Quais princípios da Convenção sobre a Diversidade Biológica são considerados?",
            ][:limit]

        # Converter para o formato de resposta
        return [SuggestedQuestion(question=q) for q in questions]

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao obter sugestões: {str(e)}"
        )


@router.post("/feedback", status_code=status.HTTP_200_OK)
async def submit_feedback(feedback: FeedbackRequest):
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
        raise HTTPException(
            status_code=500, detail=f"Erro ao processar feedback: {str(e)}"
        )
