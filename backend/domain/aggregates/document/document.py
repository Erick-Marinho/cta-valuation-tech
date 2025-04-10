"""
Modelo de domínio para representar documentos na aplicação CTA Value Tech.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime


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
    upload_date: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Atributos calculados ou de estado pós-processamento
    chunks_count: int = 0
    processed: bool = False
    size_kb: float = 0.0

    @property
    def file_extension(self) -> str:
        """
        Retorna a extensão do arquivo.

        Returns:
            str: Extensão do arquivo (sem o ponto)
        """
        if not self.name:
            return ""

        parts = self.name.split(".")
        if len(parts) > 1:
            return parts[-1].lower()
        return ""

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
            include_content: Se True, inclui o conteúdo binário (agora ignorado)

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
            "size_kb": self.size_kb,
        }

        return result
