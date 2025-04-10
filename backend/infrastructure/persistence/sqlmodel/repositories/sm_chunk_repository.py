import logging
from typing import List, Optional, Tuple, Dict
import json
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete as sqlalchemy_delete, select, text, func, cast, Float
from sqlalchemy.dialects.postgresql import JSONB

# Importar interface do domínio e entidade do domínio
from domain.repositories.chunk_repository import ChunkRepository
from domain.aggregates.document.chunk import Chunk # Importar Chunk do domínio

# Importar modelo SQLModel do banco e tipo Vector
from infrastructure.persistence.sqlmodel.models import ChunkDB, DocumentoDB # Importar ambos
from pgvector.sqlalchemy import Vector # Importar Vector

logger = logging.getLogger(__name__)

class SqlModelChunkRepository(ChunkRepository):
    """ Implementação do ChunkRepository usando SQLModel e AsyncSession. """

    def __init__(self, session: AsyncSession):
        self._session = session

    # --- Funções Auxiliares de Mapeamento ---

    def _map_db_to_domain(self, db_chunk: Optional[ChunkDB]) -> Optional[Chunk]:
        """ Mapeia o modelo SQLModel (DB) para a entidade do domínio. """
        if db_chunk is None:
            return None

        metadata_dict = {}
        metadata_from_db = db_chunk.metadados

        # Lidar com JSONB ou string JSON
        if isinstance(metadata_from_db, dict): # Já é um dict (provavelmente JSONB)
            metadata_dict = metadata_from_db
        elif isinstance(metadata_from_db, str): # Tentar decodificar string JSON
            try:
                metadata_dict = json.loads(metadata_from_db)
            except json.JSONDecodeError:
                logger.error(f"Falha ao decodificar JSON de metadados para chunk ID {db_chunk.id}: '{metadata_from_db}'")
                metadata_dict = {"error": "invalid_metadata_format"}
        elif metadata_from_db is not None:
             logger.warning(f"Metadados do chunk ID {db_chunk.id} não são dict ou str, mas {type(metadata_from_db)}. Usando vazio.")

        return Chunk(
            id=db_chunk.id,
            document_id=db_chunk.documento_id,
            text=db_chunk.texto,
            embedding=db_chunk.embedding, # Assumindo List[float] vindo do DB via pgvector/SQLAlchemy
            page_number=db_chunk.pagina,
            position=db_chunk.posicao,
            metadata=metadata_dict
        )

    def _map_domain_to_db(self, domain_chunk: Chunk) -> ChunkDB:
        """ Mapeia a entidade do domínio para o modelo SQLModel (DB). """
        return ChunkDB(
            id=domain_chunk.id,
            documento_id=domain_chunk.document_id,
            texto=domain_chunk.text,
            embedding=domain_chunk.embedding,
            pagina=domain_chunk.page_number,
            posicao=domain_chunk.position,
            metadados=json.dumps(domain_chunk.metadata) if isinstance(domain_chunk.metadata, dict) else domain_chunk.metadata
        )

    # --- Implementação dos Métodos do Repositório ---

    async def save(self, chunk: Chunk) -> Chunk:
        """ Salva (cria ou atualiza) um chunk. """
        # Nota: Atualização de chunk individual pode ser menos comum. Foco na inserção.
        try:
            db_chunk: Optional[ChunkDB] = None
            if chunk.id:
                db_chunk = await self._session.get(ChunkDB, chunk.id)
                if db_chunk:
                    # Atualizar campos se necessário (exemplo)
                    db_chunk.texto = chunk.text
                    db_chunk.embedding = chunk.embedding
                    db_chunk.metadados = chunk.metadata
                    # ... outros campos ...
                    logger.debug(f"Preparando para atualizar ChunkDB ID: {chunk.id}")
                else:
                     raise ValueError(f"Chunk com ID {chunk.id} não encontrado para atualização.")
            else:
                 db_chunk = self._map_domain_to_db(chunk)
                 self._session.add(db_chunk)
                 logger.debug(f"Preparando para inserir novo ChunkDB para Doc ID: {chunk.document_id}")

            await self._session.commit()
            await self._session.refresh(db_chunk)
            logger.info(f"Chunk salvo com ID: {db_chunk.id}")
            return self._map_db_to_domain(db_chunk)

        except Exception as e:
            logger.exception(f"Erro ao salvar chunk (ID: {chunk.id}, Doc ID: {chunk.document_id}): {e}")
            await self._session.rollback()
            raise

    async def save_batch(self, chunks: List[Chunk]) -> List[Chunk]:
        """ Salva uma lista de chunks de forma eficiente usando add_all. """
        if not chunks:
            return []
        try:
            db_chunks = [self._map_domain_to_db(c) for c in chunks]
            self._session.add_all(db_chunks)
            await self._session.commit()
            # Nota: add_all + commit geralmente não atualiza os IDs nos objetos db_chunks.
            # Se precisarmos dos IDs, teríamos que fazer um SELECT depois ou usar outra estratégia.
            # Por enquanto, retornamos os objetos do domínio originais (sem ID preenchido para novos).
            logger.info(f"{len(chunks)} chunks salvos em lote para documento ID {chunks[0].document_id if chunks else 'N/A'}.")
            # Mapear de volta pode ser ineficiente e sem IDs para novos. Retornar originais.
            return chunks
        except Exception as e:
            logger.exception(f"Erro ao salvar chunks em lote para documento ID {chunks[0].document_id if chunks else 'N/A'}: {e}")
            await self._session.rollback()
            raise

    async def find_by_id(self, chunk_id: int) -> Optional[Chunk]:
        """ Busca um chunk pelo seu ID. """
        try:
            db_chunk = await self._session.get(ChunkDB, chunk_id)
            return self._map_db_to_domain(db_chunk)
        except Exception as e:
             logger.exception(f"Erro ao buscar chunk por ID {chunk_id}: {e}")
             return None

    async def find_by_document_id(self, document_id: int) -> List[Chunk]:
        """ Busca todos os chunks associados a um documento ID. """
        try:
            statement = select(ChunkDB).where(ChunkDB.documento_id == document_id).order_by(ChunkDB.posicao)
            results = await self._session.execute(statement)
            db_chunks = results.scalars().all() # Usar scalars() para obter objetos ChunkDB diretamente
            domain_chunks = [domain_chunk for db_chunk in db_chunks if (domain_chunk := self._map_db_to_domain(db_chunk)) is not None]
            return domain_chunks
        except Exception as e:
            logger.exception(f"Erro ao buscar chunks para documento ID {document_id}: {e}")
            return []

    async def delete_by_document_id(self, document_id: int) -> int:
        """ Exclui todos os chunks associados a um documento ID. Retorna a contagem excluída. """
        try:
            # Usar delete do SQLAlchemy
            statement = sqlalchemy_delete(ChunkDB).where(ChunkDB.documento_id == document_id)
            result = await self._session.execute(statement)
            await self._session.commit()
            deleted_count = result.rowcount
            logger.info(f"{deleted_count} chunks excluídos para documento ID {document_id}.")
            return deleted_count if deleted_count is not None else 0
        except Exception as e:
            logger.exception(f"Erro ao excluir chunks para documento ID {document_id}: {e}")
            await self._session.rollback()
            return 0 # Retorna 0 em caso de erro

    # --- Implementação da Busca Textual (FTS) ---
    async def find_by_fts(
        self,
        query_text: str,
        limit: int = 10,
        document_ids: Optional[List[int]] = None,
        config: str = 'portuguese' # Configuração FTS
    ) -> List[Tuple[Chunk, float]]:
        """ Busca chunks usando Full-Text Search (FTS) do PostgreSQL. """
        logger.debug(f"Iniciando find_by_fts: limit={limit}, filter_docs={document_ids is not None}")
        try:
            ts_query_expr = func.plainto_tsquery(config, query_text)
            ts_vector_expr = func.to_tsvector(config, ChunkDB.texto)
            rank_expr = func.ts_rank(ts_vector_expr, ts_query_expr).label('rank')

            stmt = select(
                ChunkDB,
                rank_expr
            ).select_from(ChunkDB).where(
                ts_vector_expr.op('@@')(ts_query_expr)
            )

            if document_ids:
                stmt = stmt.where(ChunkDB.documento_id.in_(document_ids))

            stmt = stmt.order_by(rank_expr.desc()).limit(limit)

            results = await self._session.execute(stmt)
            db_chunks_with_rank = results.all()

            fts_chunks: List[Tuple[Chunk, float]] = []
            for db_chunk, rank in db_chunks_with_rank:
                domain_chunk = self._map_db_to_domain(db_chunk)
                if domain_chunk:
                    fts_chunks.append((domain_chunk, float(rank)))
                    # logger.debug(f"Chunk FTS encontrado: ID={domain_chunk.id}, Rank={rank:.4f}") # Log um pouco verboso aqui

            logger.info(f"Busca FTS encontrou {len(fts_chunks)} chunks.")
            return fts_chunks

        except Exception as e:
            logger.exception(f"Erro durante a busca FTS: {e}")
            return []

    # --- Implementação da Busca Vetorial ---
    async def find_similar(
        self,
        embedding: List[float],
        limit: int = 5,
        document_ids: Optional[List[int]] = None,
        # threshold: Optional[float] = None # Adicionar threshold se necessário
    ) -> List[Tuple[Chunk, float]]:
        """
        Busca chunks semanticamente similares a um embedding usando distância cosseno.

        Args:
            embedding: O vetor de embedding da consulta.
            limit: O número máximo de chunks a retornar.
            document_ids: Lista opcional de IDs de documentos para filtrar a busca.
            # threshold: Limiar opcional de distância (menor é mais similar).

        Returns:
            Uma lista de tuplas, onde cada tupla contém o objeto Chunk (domínio)
            e a distância cosseno (float). A lista é ordenada pela distância (menor primeiro).
        """
        logger.debug(f"Iniciando find_similar: limit={limit}, filter_docs={document_ids is not None}")
        try:
            # Seleciona a entidade ChunkDB e a distância cosseno
            # Nota: Usamos '<->' que é o operador de distância cosseno em pgvector
            distance_expression = ChunkDB.embedding.cosine_distance(embedding)

            stmt = select(
                ChunkDB,
                distance_expression.label('distance') # Rotula a distância calculada como 'distance'
            ).select_from(ChunkDB) # Especificar a tabela explicitamente

            # Adicionar filtro por document_ids se fornecido
            if document_ids:
                stmt = stmt.where(ChunkDB.documento_id.in_(document_ids))
                logger.debug(f"Aplicando filtro para document_ids: {document_ids}")

            # Adicionar filtro por threshold se necessário
            # if threshold is not None:
            #    stmt = stmt.where(distance_expression <= threshold) # Distância cosseno <= threshold
            #    logger.debug(f"Aplicando filtro de threshold: distance <= {threshold}")

            # Ordenar pela distância (menor primeiro para cosseno) e limitar
            stmt = stmt.order_by(distance_expression.asc()).limit(limit)

            # Executar a query
            results = await self._session.execute(stmt)
            db_chunks_with_distance = results.all() # Retorna tuplas (ChunkDB, distance)

            # Mapear resultados para o domínio
            similar_chunks: List[Tuple[Chunk, float]] = []
            for db_chunk, distance in db_chunks_with_distance:
                domain_chunk = self._map_db_to_domain(db_chunk)
                if domain_chunk:
                    # A distância retornada pelo operador '<->' já é um float
                    similar_chunks.append((domain_chunk, float(distance)))
                    logger.debug(f"Chunk encontrado: ID={domain_chunk.id}, Dist={distance:.4f}")

            logger.info(f"Busca por similaridade encontrou {len(similar_chunks)} chunks.")
            return similar_chunks

        except Exception as e:
            logger.exception(f"Erro durante a busca por similaridade: {e}")
            return []

    # --- Implementação da Busca Híbrida (NOVO - USANDO RRF) ---
    async def hybrid_search(
        self,
        query_text: str,
        embedding: List[float],
        limit: int = 5,
        document_ids: Optional[List[int]] = None,
        alpha: float = 0.5, # Mantido para logs ou futuras estratégias
        k_rrf: int = 60 # Constante k para RRF
    ) -> List[Tuple[Chunk, float]]:
        """ Realiza busca híbrida combinando busca vetorial e FTS usando RRF. """
        logger.info(f"Iniciando hybrid_search com RRF: limit={limit}, alpha={alpha}")

        # Buscar mais resultados individuais para ter chance de overlap no RRF
        individual_limit = limit * 4 # Ajustável

        # Realizar as buscas individuais em paralelo
        try:
            # --- ADICIONAR ESTA LINHA ANTES DO GATHER ---
            # Garante que a conexão da sessão esteja pronta antes das chamadas concorrentes
            logger.debug("Garantindo conexão da sessão antes das buscas concorrentes...")
            await self._session.connection()
            logger.debug("Conexão da sessão garantida.")
            # ---------------------------------------------

            vector_results_task = self.find_similar(embedding, individual_limit, document_ids)
            fts_results_task = self.find_by_fts(query_text, individual_limit, document_ids)

            vector_results, fts_results = await asyncio.gather(
                vector_results_task,
                fts_results_task,
                return_exceptions=True # Capturar exceções de buscas individuais
            )

            # Verificar erros nas tarefas individuais
            if isinstance(vector_results, Exception):
                 logger.error(f"Erro na busca vetorial durante hybrid_search: {vector_results}")
                 vector_results = []
            if isinstance(fts_results, Exception):
                 logger.error(f"Erro na busca FTS durante hybrid_search: {fts_results}")
                 fts_results = []

            logger.info(f"Resultados individuais para RRF: Vetorial={len(vector_results)}, FTS={len(fts_results)}")
        except Exception as gather_exc:
             logger.error(f"Erro inesperado ao executar buscas individuais em paralelo: {gather_exc}")
             return []

        # Criar mapas de rank {chunk_id: rank}
        vector_rank_map: Dict[int, int] = {chunk.id: rank + 1 for rank, (chunk, _) in enumerate(vector_results) if chunk.id is not None}
        fts_rank_map: Dict[int, int] = {chunk.id: rank + 1 for rank, (chunk, _) in enumerate(fts_results) if chunk.id is not None}

        # Combinar todos os chunks únicos {chunk_id: Chunk}
        all_chunks_map: Dict[int, Chunk] = {}
        all_results_combined = vector_results + fts_results # Combinar listas
        for chunk, _ in all_results_combined:
            if chunk.id is not None and chunk.id not in all_chunks_map:
                all_chunks_map[chunk.id] = chunk

        # Calcular scores RRF
        rrf_scores: List[Tuple[Chunk, float]] = []
        for chunk_id, chunk in all_chunks_map.items():
            vector_rank = vector_rank_map.get(chunk_id)
            fts_rank = fts_rank_map.get(chunk_id)
            rrf_score = 0.0
            if vector_rank is not None: rrf_score += 1.0 / (k_rrf + vector_rank)
            if fts_rank is not None: rrf_score += 1.0 / (k_rrf + fts_rank)

            if rrf_score > 0:
                 rrf_scores.append((chunk, rrf_score))
                 # logger.debug(f"Chunk ID {chunk_id}: RRF Score={rrf_score:.6f} (VecRank={vector_rank}, FTSRank={fts_rank})") # Verboso

        # Ordenar pelo score RRF (maior primeiro) e limitar
        rrf_scores.sort(key=lambda item: item[1], reverse=True)
        final_results = rrf_scores[:limit]

        logger.info(f"Busca híbrida RRF finalizou com {len(final_results)} chunks.")
        return final_results

    async def get_chunk_by_id(self, chunk_id: int):
        """Recupera um chunk específico pelo ID."""
        try:
            from sqlalchemy import text
            
            # Usar SQLAlchemy text() corretamente para declarar a expressão SQL
            query = text("""
                SELECT id, documento_id, texto as content, pagina, posicao, metadados 
                FROM chunks_vetorizados 
                WHERE id = :chunk_id
            """)
            
            # Executar query com parâmetros adequadamente
            result = await self._session.execute(query, {"chunk_id": chunk_id})
            row = result.fetchone()
            
            if row:
                # Criar um objeto com os campos necessários
                from types import SimpleNamespace
                # Usando SimpleNamespace como uma forma conveniente de criar um objeto com atributos
                chunk = SimpleNamespace(
                    id=row.id,
                    documento_id=row.documento_id,
                    content=row.content,
                    pagina=row.pagina,
                    posicao=row.posicao,
                    metadados=row.metadados
                )
                return chunk
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar chunk por ID {chunk_id}: {e}")
            return None
