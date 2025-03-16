"""
Modelo de domínio para representar documentos na aplicação CTA Value Tech.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

@dataclass
class Document:
    """
    Representa um documento no domínio da aplicação.
    
    Este modelo contém os atributos e comportamentos relacionados a documentos
    do ponto de vista da lógica de negócio, independente de como são armazenados.
    """
    id: Optional[int] = None
    name: str = ""
    file_type: str = ""
    content: bytes = field(default_factory=bytes)
    upload_date: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Atributos calculados
    chunks_count: int = 0
    processed: bool = False
    
    @property
    def file_extension(self) -> str:
        """
        Retorna a extensão do arquivo.
        
        Returns:
            str: Extensão do arquivo (sem o ponto)
        """
        if not self.name:
            return ""
            
        parts = self.name.split('.')
        if len(parts) > 1:
            return parts[-1].lower()
        return ""
    
    @property
    def size_kb(self) -> float:
        """
        Retorna o tamanho do arquivo em KB.
        
        Returns:
            float: Tamanho em KB
        """
        return len(self.content) / 1024
    
    @property
    def is_pdf(self) -> bool:
        """
        Verifica se o documento é um PDF.
        
        Returns:
            bool: True se for PDF, False caso contrário
        """
        return self.file_extension.lower() == "pdf"
    
    def to_dict(self, include_content: bool = False) -> Dict[str, Any]:
        """
        Converte o documento para um dicionário.
        
        Args:
            include_content: Se True, inclui o conteúdo binário
            
        Returns:
            dict: Representação do documento como dicionário
        """
        result = {
            "id": self.id,
            "name": self.name,
            "file_type": self.file_type,
            "upload_date": self.upload_date.isoformat(),
            "metadata": self.metadata,
            "chunks_count": self.chunks_count,
            "processed": self.processed,
            "size_kb": self.size_kb
        }
        
        if include_content:
            result["content"] = self.content
            
        return result
    
    @classmethod
    def from_db_model(cls, db_document):
        """
        Cria um Document a partir do modelo de banco de dados.
        
        Args:
            db_document: Modelo de documento do banco de dados
            
        Returns:
            Document: Nova instância de Document
        """
        if not db_document:
            return None
            
        return cls(
            id=db_document.id,
            name=db_document.nome_arquivo,
            file_type=db_document.tipo_arquivo,
            content=db_document.conteudo_binario,
            upload_date=db_document.data_upload,
            metadata=db_document.metadados,
            chunks_count=db_document.total_chunks,
            processed=db_document.total_chunks > 0
        )
    
    def to_db_model(self):
        """
        Converte para o modelo de banco de dados.
        
        Returns:
            Documento: Modelo de documento do banco de dados
        """
        from db.models.documento import Documento
        
        return Documento(
            id=self.id,
            nome_arquivo=self.name,
            tipo_arquivo=self.file_type,
            conteudo_binario=self.content,
            data_upload=self.upload_date,
            metadados=self.metadata,
            total_chunks=self.chunks_count
        )