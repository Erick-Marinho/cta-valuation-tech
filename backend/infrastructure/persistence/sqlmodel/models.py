import datetime
from typing import List, Optional, Dict, Any
import sqlalchemy as sa # Importar sqlalchemy para sa.text
from sqlmodel import Field, SQLModel, JSON, Column
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

# Dimensão do Embedding (ajuste se necessário)
EMBEDDING_DIM = 1024

class DocumentoDB(SQLModel, table=True):
    """ Modelo SQLModel para a tabela 'documentos_originais'. """
    __tablename__ = "documentos_originais"

    id: Optional[int] = Field(default=None, primary_key=True)
    nome_arquivo: str = Field(index=True, nullable=False)
    tipo_arquivo: Optional[str] = Field(default=None)
    # conteudo_binario: Optional[bytes] = Field(default=None) # Omitido
    data_upload: Optional[datetime.datetime] = Field(
        default=None, # Deixar o DB gerar o default
        sa_column_kwargs={"server_default": sa.text("CURRENT_TIMESTAMP")}
    )
    metadados: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column(JSONB))

class ChunkDB(SQLModel, table=True):
    """ Modelo SQLModel para a tabela 'chunks_vetorizados'. """
    __tablename__ = "chunks_vetorizados"

    id: Optional[int] = Field(default=None, primary_key=True)
    documento_id: int = Field(foreign_key="documentos_originais.id", index=True, nullable=False)
    texto: str = Field(nullable=False)
    embedding: List[float] = Field(sa_column=Column(Vector(EMBEDDING_DIM)))
    pagina: Optional[int] = Field(default=None)
    posicao: Optional[int] = Field(default=None)
    metadados: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column(JSONB))
