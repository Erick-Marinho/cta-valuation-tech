"""
Modelo para representar chunks vetorizados no banco de dados.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import json


@dataclass
class Chunk:
    """
    Representa um chunk vetorizado de texto.
    """

    id: Optional[int] = None
    documento_id: Optional[int] = None
    texto: str = ""
    embedding: List[float] = field(default_factory=list)
    pagina: Optional[int] = None
    posicao: Optional[int] = None
    metadados: Dict[str, Any] = field(default_factory=dict)

    # Campos calculados/relacionados
    arquivo_origem: str = ""
    similarity_score: float = 0.0
    text_score: float = 0.0
    combined_score: float = 0.0

    @classmethod
    def from_db_row(cls, row):
        """
        Cria uma instância de Chunk a partir de uma linha do banco de dados.

        Args:
            row (dict): Linha do banco de dados

        Returns:
            Chunk: Instância do modelo
        """
        if row is None:
            return None

        chunk = cls()
        chunk.id = row.get("id")
        chunk.documento_id = row.get("documento_id")
        chunk.texto = row.get("texto", "")

        # O embedding pode ser None em algumas consultas onde não é selecionado
        if "embedding" in row and row["embedding"] is not None:
            # Converter de formato pgvector para lista Python
            chunk.embedding = list(row["embedding"])

        chunk.pagina = row.get("pagina")
        chunk.posicao = row.get("posicao")

        # Processar metadados
        if row.get("metadados"):
            if isinstance(row.get("metadados"), str):
                chunk.metadados = json.loads(row.get("metadados"))
            else:
                chunk.metadados = row.get("metadados")

        # Campos calculados/relacionados
        chunk.arquivo_origem = row.get("arquivo_origem", "")

        # Scores (podem não estar presentes em todas as consultas)
        chunk.similarity_score = float(row.get("similarity_score", 0))
        chunk.text_score = float(row.get("text_score", 0))
        chunk.combined_score = float(row.get("combined_score", 0))

        return chunk

    def to_dict(self, include_embedding=False):
        """
        Converte o modelo para um dicionário.

        Args:
            include_embedding (bool): Se True, inclui o embedding

        Returns:
            dict: Representação do chunk como dicionário
        """
        result = {
            "id": self.id,
            "documento_id": self.documento_id,
            "texto": self.texto,
            "pagina": self.pagina,
            "posicao": self.posicao,
            "metadados": self.metadados,
            "arquivo_origem": self.arquivo_origem,
            "similarity_score": self.similarity_score,
            "text_score": self.text_score,
            "combined_score": self.combined_score,
        }

        if include_embedding:
            result["embedding"] = self.embedding

        return result

    @property
    def tamanho_caracteres(self):
        """
        Retorna o tamanho do texto em caracteres.

        Returns:
            int: Número de caracteres
        """
        return len(self.texto)

    @property
    def tamanho_tokens(self):
        """
        Estimativa grosseira do número de tokens baseado no número de palavras.
        Para uma estimativa mais precisa, use um tokenizador específico do modelo.

        Returns:
            int: Estimativa do número de tokens
        """
        return len(self.texto.split())
