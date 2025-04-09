"""
Modelo de domínio para representar chunks de texto na aplicação.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class Chunk:
    """
    Representa um chunk de texto no domínio da aplicação.

    Este modelo é a representação de negócio de um chunk,
    independente de como é armazenado no banco de dados.
    """

    id: Optional[int] = None
    document_id: Optional[int] = None
    text: str = ""
    embedding: List[float] = field(default_factory=list)
    page_number: Optional[int] = None
    position: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Campos calculados/relacionados
    source_document: str = ""
    similarity_score: float = 0.0
    text_score: float = 0.0
    combined_score: float = 0.0

    @property
    def char_count(self) -> int:
        """
        Retorna o número de caracteres no texto.

        Returns:
            int: Número de caracteres
        """
        return len(self.text)

    @property
    def token_count(self) -> int:
        """
        Estimativa do número de tokens no texto.

        Returns:
            int: Número estimado de tokens
        """
        return len(self.text.split())

    def to_dict(self, include_embedding: bool = False) -> Dict[str, Any]:
        """
        Converte o chunk para um dicionário.

        Args:
            include_embedding: Se True, inclui o embedding

        Returns:
            dict: Representação do chunk como dicionário
        """
        result = {
            "id": self.id,
            "document_id": self.document_id,
            "text": self.text,
            "page_number": self.page_number,
            "position": self.position,
            "metadata": self.metadata,
            "source_document": self.source_document,
            "similarity_score": self.similarity_score,
            "text_score": self.text_score,
            "combined_score": self.combined_score,
            "char_count": self.char_count,
            "token_count": self.token_count,
        }

        if include_embedding:
            result["embedding"] = self.embedding

        return result
