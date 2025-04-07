"""
Repositório para operações relacionadas a documentos.
"""

import logging
from typing import List, Optional, Dict, Any
from psycopg2.extras import Json
from psycopg2.extensions import Binary
from ..connection import execute_query, execute_query_single_result
from ..models.document import Documento

logger = logging.getLogger(__name__)


class DocumentoRepository:
    """
    Repositório para operações relacionadas a documentos no banco de dados.
    """

    @staticmethod
    def criar_documento(
        nome_arquivo: str,
        tipo_arquivo: str,
        conteudo_binario: bytes,
        metadados: Dict[str, Any] = None,
    ) -> Optional[int]:
        """
        Insere um novo documento no banco de dados.

        Args:
            nome_arquivo (str): Nome do arquivo
            tipo_arquivo (str): Tipo/extensão do arquivo
            conteudo_binario (bytes): Conteúdo binário do arquivo
            metadados (dict): Metadados adicionais

        Returns:
            int: ID do documento criado, ou None em caso de erro
        """
        try:
            result = execute_query_single_result(
                """
                INSERT INTO documentos_originais (nome_arquivo, tipo_arquivo, conteudo_binario, metadados)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (
                    nome_arquivo,
                    tipo_arquivo,
                    Binary(conteudo_binario),
                    Json(metadados or {}),
                ),
            )

            if result and "id" in result:
                documento_id = result["id"]
                logger.info(f"Documento criado com ID {documento_id}")
                return documento_id
            return None

        except Exception as e:
            logger.error(f"Erro ao criar documento: {e}")
            return None

    @staticmethod
    def obter_por_id(documento_id: int) -> Optional[Documento]:
        """
        Obtém um documento pelo ID.

        Args:
            documento_id (int): ID do documento

        Returns:
            Documento: Instância do documento, ou None se não encontrado
        """
        try:
            row = execute_query_single_result(
                """
                SELECT 
                    d.*,
                    (SELECT COUNT(*) FROM chunks_vetorizados WHERE documento_id = d.id) as chunks_count
                FROM 
                    documentos_originais d
                WHERE 
                    d.id = %s
                """,
                (documento_id,),
            )

            if not row:
                return None

            return Documento.from_db_row(row)

        except Exception as e:
            logger.error(f"Erro ao obter documento por ID {documento_id}: {e}")
            return None

    @staticmethod
    def listar_todos(incluir_conteudo: bool = False) -> List[Documento]:
        """
        Lista todos os documentos no banco de dados.

        Args:
            incluir_conteudo (bool): Se True, inclui o conteúdo binário na resposta

        Returns:
            list: Lista de documentos
        """
        try:
            content_field = ", conteudo_binario" if incluir_conteudo else ""

            rows = execute_query(
                f"""
                SELECT 
                    id, 
                    nome_arquivo, 
                    tipo_arquivo, 
                    data_upload, 
                    metadados{content_field},
                    (SELECT COUNT(*) FROM chunks_vetorizados WHERE documento_id = documentos_originais.id) as chunks_count
                FROM 
                    documentos_originais
                ORDER BY 
                    data_upload DESC
                """
            )

            documentos = []
            for row in rows:
                documento = Documento.from_db_row(row)
                documentos.append(documento)

            return documentos

        except Exception as e:
            logger.error(f"Erro ao listar documentos: {e}")
            return []

    @staticmethod
    def excluir_documento(documento_id: int) -> bool:
        """
        Exclui um documento do banco de dados.
        Os chunks associados são excluídos automaticamente pela restrição ON DELETE CASCADE.

        Args:
            documento_id (int): ID do documento a ser excluído

        Returns:
            bool: True se o documento foi excluído com sucesso, False caso contrário
        """
        try:
            execute_query(
                "DELETE FROM documentos_originais WHERE id = %s",
                (documento_id,),
                fetch=False,
            )

            logger.info(f"Documento {documento_id} excluído com sucesso")
            return True

        except Exception as e:
            logger.error(f"Erro ao excluir documento {documento_id}: {e}")
            return False

    @staticmethod
    def atualizar_metadados(documento_id: int, metadados: Dict[str, Any]) -> bool:
        """
        Atualiza os metadados de um documento.

        Args:
            documento_id (int): ID do documento
            metadados (dict): Novos metadados

        Returns:
            bool: True se os metadados foram atualizados com sucesso, False caso contrário
        """
        try:
            execute_query(
                """
                UPDATE documentos_originais
                SET metadados = %s
                WHERE id = %s
                """,
                (Json(metadados), documento_id),
                fetch=False,
            )

            logger.info(
                f"Metadados do documento {documento_id} atualizados com sucesso"
            )
            return True

        except Exception as e:
            logger.error(
                f"Erro ao atualizar metadados do documento {documento_id}: {e}"
            )
            return False

    @staticmethod
    def buscar_por_nome(termo_busca: str) -> List[Documento]:
        """
        Busca documentos por nome do arquivo.

        Args:
            termo_busca (str): Termo para busca no nome do arquivo

        Returns:
            list: Lista de documentos que correspondem à busca
        """
        try:
            # Adicionar % para busca parcial
            termo_busca = f"%{termo_busca}%"

            rows = execute_query(
                """
                SELECT 
                    id, 
                    nome_arquivo, 
                    tipo_arquivo, 
                    data_upload, 
                    metadados,
                    (SELECT COUNT(*) FROM chunks_vetorizados WHERE documento_id = documentos_originais.id) as chunks_count
                FROM 
                    documentos_originais
                WHERE 
                    nome_arquivo ILIKE %s
                ORDER BY 
                    data_upload DESC
                """,
                (termo_busca,),
            )

            documentos = []
            for row in rows:
                documento = Documento.from_db_row(row)
                documentos.append(documento)

            return documentos

        except Exception as e:
            logger.error(f"Erro ao buscar documentos por nome '{termo_busca}': {e}")
            return []

    @staticmethod
    def contar_documentos() -> int:
        """
        Conta o número total de documentos no banco de dados.

        Returns:
            int: Número total de documentos
        """
        try:
            result = execute_query_single_result(
                "SELECT COUNT(*) as total FROM documentos_originais"
            )

            if result and "total" in result:
                return result["total"]
            return 0

        except Exception as e:
            logger.error(f"Erro ao contar documentos: {e}")
            return 0
