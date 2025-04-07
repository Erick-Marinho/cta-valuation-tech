"""
Modelo para representar documentos originais no banco de dados.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
import json


@dataclass
class Documento:
    """
    Representa um documento original armazenado no banco de dados.
    """

    id: Optional[int] = None
    nome_arquivo: str = ""
    tipo_arquivo: str = ""
    conteudo_binario: bytes = field(default_factory=bytes)
    data_upload: datetime = field(default_factory=datetime.now)
    metadados: Dict[str, Any] = field(default_factory=dict)

    # Campos calculados/relacionados
    total_chunks: int = 0

    @classmethod
    def from_db_row(cls, row):
        """
        Cria uma instância de Documento a partir de uma linha do banco de dados.

        Args:
            row (dict): Linha do banco de dados

        Returns:
            Documento: Instância do modelo
        """
        if row is None:
            return None

        doc = cls()
        doc.id = row.get("id")
        doc.nome_arquivo = row.get("nome_arquivo", "")
        doc.tipo_arquivo = row.get("tipo_arquivo", "")

        # O conteúdo binário pode ser None em algumas consultas onde não é selecionado
        doc.conteudo_binario = row.get("conteudo_binario", bytes())

        # Converter a data de string para datetime se necessário
        if isinstance(row.get("data_upload"), str):
            doc.data_upload = datetime.fromisoformat(row.get("data_upload"))
        else:
            doc.data_upload = row.get("data_upload", datetime.now())

        # Processar metadados
        if row.get("metadados"):
            if isinstance(row.get("metadados"), str):
                doc.metadados = json.loads(row.get("metadados"))
            else:
                doc.metadados = row.get("metadados")

        # Campos calculados
        doc.total_chunks = row.get("chunks_count", 0)

        return doc

    def to_dict(self, include_content=False):
        """
        Converte o modelo para um dicionário.

        Args:
            include_content (bool): Se True, inclui o conteúdo binário

        Returns:
            dict: Representação do documento como dicionário
        """
        result = {
            "id": self.id,
            "nome": self.nome_arquivo,
            "tipo": self.tipo_arquivo,
            "data_upload": self.data_upload.isoformat(),
            "metadados": self.metadados,
            "total_chunks": self.total_chunks,
        }

        if include_content:
            result["conteudo_binario"] = self.conteudo_binario

        return result

    @property
    def extensao(self):
        """
        Retorna a extensão do arquivo.

        Returns:
            str: Extensão do arquivo (sem o ponto)
        """
        if not self.nome_arquivo:
            return ""

        partes = self.nome_arquivo.split(".")
        if len(partes) > 1:
            return partes[-1].lower()
        return ""

    @property
    def tamanho_kb(self):
        """
        Retorna o tamanho do arquivo em KB.

        Returns:
            float: Tamanho em KB
        """
        return len(self.conteudo_binario) / 1024
