"""
Modelo de domínio para representar chunks de texto na aplicação.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class Chunk:
    """
    Representa um chunk de texto no domínio da aplicação.

    Focado no conteúdo textual, localização e metadados relevantes ao negócio,
    independente de detalhes de implementação como embeddings ou scores de busca.
    """

    id: Optional[int] = None
    document_id: Optional[int] = None
    text: str = ""
    page_number: Optional[int] = None
    position: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

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

    def to_dict(self) -> Dict[str, Any]:
        """
        Converte o chunk para um dicionário.

        Returns:
            dict: Representação do chunk como dicionário
        """
        return {
            "id": self.id,
            "document_id": self.document_id,
            "text": self.text,
            "page_number": self.page_number,
            "position": self.position,
            "metadata": self.metadata,
            "char_count": self.char_count,
            "token_count": self.token_count,
        }
