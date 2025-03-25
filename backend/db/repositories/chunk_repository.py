"""
Repositório para operações relacionadas a chunks vetorizados.
"""
import logging
from typing import List, Optional, Dict, Any
from psycopg2.extras import Json
from ..connection import execute_query, execute_query_single_result
from ..models.chunk import Chunk

logger = logging.getLogger(__name__)

class ChunkRepository:
    """
    Repositório para operações relacionadas a chunks no banco de dados.
    """
    
    @staticmethod
    def criar_chunk(documento_id: int, texto: str, embedding: List[float], 
                  pagina: Optional[int] = None, posicao: Optional[int] = None,
                  metadados: Dict[str, Any] = None) -> Optional[int]:
        """
        Insere um novo chunk no banco de dados.
        
        Args:
            documento_id (int): ID do documento ao qual o chunk pertence
            texto (str): Texto do chunk
            embedding (list): Vetor de embedding
            pagina (int): Número da página (opcional)
            posicao (int): Posição/ordem do chunk no documento (opcional)
            metadados (dict): Metadados adicionais
            
        Returns:
            int: ID do chunk criado, ou None em caso de erro
        """
        try:
            result = execute_query_single_result(
                """
                INSERT INTO chunks_vetorizados 
                (documento_id, texto, embedding, pagina, posicao, metadados)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (documento_id, texto, embedding, pagina, posicao, Json(metadados or {}))
            )
            
            if result and 'id' in result:
                chunk_id = result['id']
                logger.debug(f"Chunk criado com ID {chunk_id}")
                return chunk_id
            return None
            
        except Exception as e:
            logger.error(f"Erro ao criar chunk: {e}")
            return None
    
    @staticmethod
    def criar_chunks_em_lote(chunks_data: List[Dict[str, Any]]) -> int:
        """
        Insere múltiplos chunks em lote.
        
        Args:
            chunks_data (list): Lista de dicionários com dados dos chunks
            
        Returns:
            int: Número de chunks criados com sucesso
        """
        successful_chunks = 0
        
        try:
            for chunk_data in chunks_data:
                documento_id = chunk_data.get('documento_id')
                texto = chunk_data.get('texto', '')
                embedding = chunk_data.get('embedding', [])
                pagina = chunk_data.get('pagina')
                posicao = chunk_data.get('posicao')
                metadados = chunk_data.get('metadados', {})
                
                chunk_id = ChunkRepository.criar_chunk(
                    documento_id=documento_id,
                    texto=texto,
                    embedding=embedding,
                    pagina=pagina,
                    posicao=posicao,
                    metadados=metadados
                )
                
                if chunk_id:
                    successful_chunks += 1
            
            return successful_chunks
            
        except Exception as e:
            logger.error(f"Erro ao criar chunks em lote: {e}")
            return successful_chunks
    
    @staticmethod
    def obter_por_id(chunk_id: int) -> Optional[Chunk]:
        """
        Obtém um chunk pelo ID.
        
        Args:
            chunk_id (int): ID do chunk
            
        Returns:
            Chunk: Instância do chunk, ou None se não encontrado
        """
        try:
            row = execute_query_single_result(
                """
                SELECT 
                    cv.*,
                    (SELECT nome_arquivo FROM documentos_originais WHERE id = cv.documento_id) as arquivo_origem
                FROM 
                    chunks_vetorizados cv
                WHERE 
                    cv.id = %s
                """,
                (chunk_id,)
            )
            
            if not row:
                return None
                
            return Chunk.from_db_row(row)
            
        except Exception as e:
            logger.error(f"Erro ao obter chunk por ID {chunk_id}: {e}")
            return None
    
    @staticmethod
    def listar_por_documento(documento_id: int, incluir_embedding: bool = False) -> List[Chunk]:
        """
        Lista todos os chunks associados a um documento.
        
        Args:
            documento_id (int): ID do documento
            incluir_embedding (bool): Se True, inclui o embedding na resposta
            
        Returns:
            list: Lista de chunks do documento
        """
        try:
            embedding_field = ", embedding" if incluir_embedding else ""
            
            rows = execute_query(
                f"""
                SELECT 
                    cv.id, 
                    cv.documento_id, 
                    cv.texto, 
                    cv.pagina, 
                    cv.posicao, 
                    cv.metadados{embedding_field},
                    (SELECT nome_arquivo FROM documentos_originais WHERE id = cv.documento_id) as arquivo_origem
                FROM 
                    chunks_vetorizados cv
                WHERE 
                    cv.documento_id = %s
                ORDER BY 
                    cv.posicao
                """,
                (documento_id,)
            )
            
            chunks = []
            for row in rows:
                chunk = Chunk.from_db_row(row)
                chunks.append(chunk)
                
            return chunks
            
        except Exception as e:
            logger.error(f"Erro ao listar chunks do documento {documento_id}: {e}")
            return []
    
    @staticmethod
    def busca_vetorial(query_embedding: List[float], limite: int = 5, 
                       threshold: float = 0.6) -> List[Chunk]:
        """
        Realiza uma busca vetorial por similaridade de cosseno.
        
        Args:
            query_embedding (list): Vetor de embedding da query
            limite (int): Número máximo de resultados
            threshold (float): Limiar de similaridade (0.0 - 1.0)
            
        Returns:
            list: Lista de chunks que correspondem à busca vetorial
        """
        try:
            rows = execute_query(
                """
                SELECT 
                    cv.id, 
                    cv.documento_id, 
                    cv.texto, 
                    cv.pagina, 
                    cv.posicao, 
                    cv.metadados,
                    1 - (cv.embedding <=> %s::vector) as similarity_score,
                    (SELECT nome_arquivo FROM documentos_originais WHERE id = cv.documento_id) as arquivo_origem
                FROM 
                    chunks_vetorizados cv
                WHERE 
                    1 - (cv.embedding <=> %s::vector) > %s
                ORDER BY 
                    cv.embedding <=> %s::vector
                LIMIT %s
                """,
                (query_embedding, query_embedding, threshold, query_embedding, limite)
            )
            
            chunks = []
            for row in rows:
                chunk = Chunk.from_db_row(row)
                chunks.append(chunk)
                
            return chunks
            
        except Exception as e:
            logger.error(f"Erro na busca vetorial: {e}")
            return []
    
    @staticmethod
    def busca_textual(query_text: str, limite: int = 5) -> List[Chunk]:
        """
        Realiza uma busca textual usando full-text search do PostgreSQL.
        
        Args:
            query_text (str): Texto da query
            limite (int): Número máximo de resultados
            
        Returns:
            list: Lista de chunks que correspondem à busca textual
        """
        try:
            rows = execute_query(
                """
                SELECT 
                    cv.id, 
                    cv.documento_id, 
                    cv.texto, 
                    cv.pagina, 
                    cv.posicao, 
                    cv.metadados,
                    ts_rank_cd(to_tsvector('portuguese', cv.texto), plainto_tsquery('portuguese', %s)) as text_score,
                    (SELECT nome_arquivo FROM documentos_originais WHERE id = cv.documento_id) as arquivo_origem
                FROM 
                    chunks_vetorizados cv
                WHERE 
                    to_tsvector('portuguese', cv.texto) @@ plainto_tsquery('portuguese', %s)
                ORDER BY 
                    text_score DESC
                LIMIT %s
                """,
                (query_text, query_text, limite)
            )
            
            chunks = []
            for row in rows:
                chunk = Chunk.from_db_row(row)
                chunks.append(chunk)
                
            return chunks
            
        except Exception as e:
            logger.error(f"Erro na busca textual: {e}")
            return []
    
    @staticmethod
    def busca_hibrida(query_text: str, query_embedding: List[float], 
                     limite: int = 5, alpha: float = 0.7) -> List[Chunk]:
        """
        Realiza uma busca híbrida combinando busca vetorial e textual.
        
        Args:
            query_text (str): Texto da query
            query_embedding (list): Embedding da query
            limite (int): Número máximo de resultados
            alpha (float): Peso para busca vetorial (0.0 - 1.0)
            
        Returns:
            list: Lista de chunks ordenados por score combinado
        """
        try:
            # Busca vetorial (top 20)
            vector_rows = execute_query(
                """
                SELECT 
                    cv.id, 
                    cv.documento_id, 
                    cv.texto, 
                    cv.pagina, 
                    cv.posicao, 
                    cv.metadados,
                    1 - (cv.embedding <=> %s::vector) as similarity_score,
                    (SELECT nome_arquivo FROM documentos_originais WHERE id = cv.documento_id) as arquivo_origem
                FROM 
                    chunks_vetorizados cv
                ORDER BY 
                    cv.embedding <=> %s::vector
                LIMIT 20
                """,
                (query_embedding, query_embedding)
            )
            
            # Busca textual (top 20)
            text_rows = execute_query(
                """
                SELECT 
                    cv.id, 
                    cv.documento_id, 
                    cv.texto, 
                    cv.pagina, 
                    cv.posicao, 
                    cv.metadados,
                    ts_rank_cd(to_tsvector('portuguese', cv.texto), plainto_tsquery('portuguese', %s)) as text_score,
                    (SELECT nome_arquivo FROM documentos_originais WHERE id = cv.documento_id) as arquivo_origem
                FROM 
                    chunks_vetorizados cv
                WHERE 
                    to_tsvector('portuguese', cv.texto) @@ plainto_tsquery('portuguese', %s)
                ORDER BY 
                    text_score DESC
                LIMIT 20
                """,
                (query_text, query_text)
            )
            
            # Combinar resultados
            combined_results = {}
            
            # Processar resultados da busca vetorial
            for row in vector_rows:
                chunk_id = row['id']
                if chunk_id not in combined_results:
                    chunk = Chunk.from_db_row(row)
                    combined_results[chunk_id] = chunk
            
            # Processar resultados da busca textual
            for row in text_rows:
                chunk_id = row['id']
                text_score = float(row['text_score'])
                
                if chunk_id in combined_results:
                    # Atualizar score de texto para chunks já encontrados na busca vetorial
                    combined_results[chunk_id].text_score = text_score
                else:
                    # Buscar o score de similaridade para chunks encontrados apenas na busca textual
                    similarity_row = execute_query_single_result(
                        """
                        SELECT 
                            1 - (cv.embedding <=> %s::vector) as similarity_score
                        FROM 
                            chunks_vetorizados cv
                        WHERE 
                            cv.id = %s
                        """,
                        (query_embedding, chunk_id)
                    )
                    
                    similarity_score = 0.0
                    if similarity_row and 'similarity_score' in similarity_row:
                        similarity_score = float(similarity_row['similarity_score'])
                    
                    # Criar chunk com ambos os scores
                    chunk = Chunk.from_db_row(row)
                    chunk.similarity_score = similarity_score
                    combined_results[chunk_id] = chunk
            
            # Calcular score combinado para cada resultado
            for chunk_id, chunk in combined_results.items():
                # Normalizar text_score (assumindo que está entre 0 e 1)
                norm_text_score = min(chunk.text_score, 1.0)
                
                # Calcular score combinado usando o peso alpha
                chunk.combined_score = alpha * chunk.similarity_score + (1 - alpha) * norm_text_score
            
            # Ordenar por score combinado e limitar resultados
            sorted_chunks = sorted(
                combined_results.values(), 
                key=lambda x: x.combined_score, 
                reverse=True
            )
            
            return sorted_chunks[:limite]
            
        except Exception as e:
            logger.error(f"Erro na busca híbrida: {e}")
            return []
    
    @staticmethod
    def excluir_chunks_do_documento(documento_id: int) -> bool:
        """
        Exclui todos os chunks associados a um documento.
        
        Args:
            documento_id (int): ID do documento
            
        Returns:
            bool: True se os chunks foram excluídos com sucesso, False caso contrário
        """
        try:
            execute_query(
                "DELETE FROM chunks_vetorizados WHERE documento_id = %s",
                (documento_id,),
                fetch=False
            )
            
            logger.info(f"Chunks do documento {documento_id} excluídos com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao excluir chunks do documento {documento_id}: {e}")
            return False