"""
Modelo de domínio para representar consultas de usuários.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime


@dataclass
class Query:
    """
    Representa uma consulta de usuário no domínio da aplicação.
    """

    id: Optional[int] = None
    text: str = ""
    embedding: List[float] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Filtros opcionais para a busca
    document_ids: List[int] = field(default_factory=list)

    # Preferências de busca
    max_results: int = 5
    vector_weight: float = 0.7  # Peso para busca vetorial vs. textual

    @property
    def char_count(self) -> int:
        """
        Retorna o número de caracteres na consulta.

        Returns:
            int: Número de caracteres
        """
        return len(self.text)

    @property
    def word_count(self) -> int:
        """
        Retorna o número de palavras na consulta.

        Returns:
            int: Número de palavras
        """
        return len(self.text.split())

    def to_dict(self, include_embedding: bool = False) -> Dict[str, Any]:
        """
        Converte a consulta para um dicionário.

        Args:
            include_embedding: Se True, inclui o embedding

        Returns:
            dict: Representação da consulta como dicionário
        """
        result = {
            "id": self.id,
            "text": self.text,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "document_ids": self.document_ids,
            "max_results": self.max_results,
            "vector_weight": self.vector_weight,
            "char_count": self.char_count,
            "word_count": self.word_count,
        }

        if include_embedding and self.embedding:
            result["embedding"] = self.embedding

        return result
