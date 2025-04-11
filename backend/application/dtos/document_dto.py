from dataclasses import dataclass
# Ou use from pydantic import BaseModel
from typing import Dict, Any, Optional
import datetime # Para o tipo do campo de data

@dataclass # Ou class DocumentDTO(BaseModel):
class DocumentDTO:
    """
    Data Transfer Object para representar informações de um Documento
    retornadas pela camada de Aplicação.

    Contém apenas dados, sem lógica de negócio, e define a estrutura
    que a camada de Aplicação expõe para as camadas externas (Interface).
    """
    id: int
    name: str
    file_type: Optional[str]
    upload_date: Optional[datetime.datetime] # Manter o tipo original datetime
    size_kb: Optional[float]
    chunks_count: Optional[int]
    processed: Optional[bool]
    metadata: Dict[str, Any]

# --- Adicionar um DTO para Chunks também pode ser útil ---
@dataclass
class ChunkDTO:
    """
    DTO para informações de Chunk.
    Usado para transferir dados de chunks entre a camada de Aplicação e Interface,
    incluindo o texto completo necessário para avaliação ou exibição.
    """
    id: int
    document_id: int
    text: str  # <-- Alterado de text_preview para text (texto completo)
    page_number: Optional[int]
    position: Optional[int]
    # metadata: Optional[Dict[str, Any]] = None # Opcional: adicionar se necessário para debug/display

# --- DTO para resultados de busca (Exemplo) ---
@dataclass
class SearchResultDTO:
     """ DTO para um resultado de busca, combinando Chunk e scores. """
     chunk: ChunkDTO # Usar o ChunkDTO
     similarity_score: Optional[float] = None
     text_score: Optional[float] = None
     combined_score: Optional[float] = None
     # source_document_name: Optional[str] = None # Se necessário

# Poderíamos ter outros DTOs aqui, como ChunkDTO, QueryDTO, etc.
