import logging
from typing import List, Optional, Tuple, Dict, Any
import json
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete as sqlalchemy_delete, select, text, func, cast, Float
from sqlalchemy.dialects.postgresql import JSONB, insert as pg_insert

# Importar interface do domínio e entidade do domínio
from domain.repositories.chunk_repository import ChunkRepository
from domain.aggregates.document.chunk import Chunk # Importar Chunk do domínio

# Importar modelo SQLModel do banco e tipo Vector
from infrastructure.persistence.sqlmodel.models import ChunkDB, DocumentoDB, EMBEDDING_DIM # Importar ambos
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
            page_number=db_chunk.pagina,
            position=db_chunk.posicao,
            metadata=metadata_dict
        )

    # --- Métodos da Interface (Com assinatura limpa, mas funcionalidade limitada) ---

    async def save(self, chunk: Chunk) -> Chunk:
        """
        Salva um único chunk SEM seu embedding.
        ATENÇÃO: Geralmente não é útil, pois o embedding é crucial.
        Use save_with_embedding para salvar com o vetor.
        """
        logger.warning(f"Chamada a save() em SqlModelChunkRepository para chunk ID {chunk.id} sem embedding. O embedding NÃO será salvo/atualizado.")
        # Implementação simplificada que salva/atualiza apenas dados não-vetoriais
        try:
            if chunk.id:
                db_chunk = await self._session.get(ChunkDB, chunk.id)
                if db_chunk:
                    db_chunk.texto = chunk.text
                    db_chunk.pagina = chunk.page_number
                    db_chunk.posicao = chunk.position
                    db_chunk.metadados = chunk.metadata
                    # db_chunk.embedding NÃO é atualizado
                    logger.debug(f"Preparando para atualizar ChunkDB ID: {chunk.id} (sem embedding)")
                else:
                     raise ValueError(f"Chunk com ID {chunk.id} não encontrado para atualização.")
            else:
                 # Inserir sem embedding (se a coluna permitir NULL ou tiver default)
                 db_chunk = ChunkDB(
                     documento_id=chunk.document_id,
                     texto=chunk.text,
                     pagina=chunk.page_number,
                     posicao=chunk.position,
                     metadados=chunk.metadata,
                     embedding=None # Ou omitir se tiver default/gerado no DB
                 )
                 self._session.add(db_chunk)
                 logger.debug(f"Preparando para inserir novo ChunkDB para doc ID {chunk.document_id} (sem embedding)")

            await self._session.commit()
            await self._session.refresh(db_chunk)
            logger.info(f"Chunk salvo (sem embedding) com ID: {db_chunk.id}")
            return self._map_db_to_domain(db_chunk)

        except Exception as e:
            logger.exception(f"Erro ao salvar chunk (sem embedding) (ID: {chunk.id}, Doc ID: {chunk.document_id}): {e}")
            await self._session.rollback()
            raise

    async def save_batch(self, chunks: List[Chunk]) -> List[Chunk]:
        """
        Salva uma lista de chunks SEM seus embeddings.
        ATENÇÃO: Geralmente não é útil. Use save_batch_with_embeddings.
        """
        logger.warning(f"Chamada a save_batch() em SqlModelChunkRepository para {len(chunks)} chunks sem embeddings. Os embeddings NÃO serão salvos.")
        # Implementação levanta erro ou salva sem embeddings
        # Por simplicidade, vamos levantar erro para desencorajar o uso
        raise NotImplementedError("save_batch sem embeddings não é suportado. Use save_batch_with_embeddings.")
        # Alternativa: implementar loop chamando save() acima, mas ineficiente

    # --- Métodos Específicos da Implementação (Com Embeddings) ---

    async def save_with_embedding(self, chunk: Chunk, embedding: List[float]) -> Chunk:
         """ Salva (cria ou atualiza) um único chunk COM seu embedding. """
         # Esta é a lógica que estava anteriormente em save()
         logger.debug(f"Executando save_with_embedding para chunk (ID: {chunk.id}, Doc ID: {chunk.document_id})")
         try:
             if chunk.id:
                 # Atualizar
                 db_chunk = await self._session.get(ChunkDB, chunk.id)
                 if db_chunk:
                     db_chunk.texto = chunk.text
                     db_chunk.pagina = chunk.page_number
                     db_chunk.posicao = chunk.position
                     db_chunk.metadados = chunk.metadata
                     db_chunk.embedding = embedding # <-- Atualiza o embedding
                     logger.debug(f"Preparando para atualizar ChunkDB ID: {chunk.id} (com embedding)")
                 else:
                     raise ValueError(f"Chunk com ID {chunk.id} não encontrado para atualização.")
             else:
                 # Inserir
                 db_chunk = ChunkDB(
                     documento_id=chunk.document_id,
                     texto=chunk.text,
                     embedding=embedding, # <-- Usa o embedding passado
                     pagina=chunk.page_number,
                     posicao=chunk.position,
                     metadados=chunk.metadata
                 )
                 self._session.add(db_chunk)
                 logger.debug(f"Preparando para inserir novo ChunkDB para doc ID {chunk.document_id} (com embedding)")

             await self._session.commit()
             await self._session.refresh(db_chunk)
             logger.info(f"Chunk salvo (com embedding) com ID: {db_chunk.id}")
             return self._map_db_to_domain(db_chunk)

         except Exception as e:
             logger.exception(f"Erro ao salvar chunk com embedding (ID: {chunk.id}, Doc ID: {chunk.document_id}): {e}")
             await self._session.rollback()
             raise


    async def save_batch_with_embeddings(self, chunks_with_embeddings: List[Tuple[Chunk, List[float]]]) -> List[Chunk]:
        """ Salva uma lista de chunks com seus embeddings associados de forma eficiente. """
        # Esta é a lógica que estava anteriormente em save_batch()
        logger.debug(f"Executando save_batch_with_embeddings para {len(chunks_with_embeddings)} chunks.")
        if not chunks_with_embeddings:
            return []

        # Mapear entidades de domínio + embeddings para o formato do banco (lista de dicts)
        values_to_insert = []
        chunks_to_return: List[Chunk] = [] # Para manter a ordem e retornar
        for domain_chunk, embedding_vector in chunks_with_embeddings:
             if not domain_chunk.document_id:
                 logger.error(f"Chunk sem documento_id não pode ser salvo: {domain_chunk}")
                 continue # Pular este chunk

             values_to_insert.append({
                 "documento_id": domain_chunk.document_id,
                 "texto": domain_chunk.text,
                 "embedding": embedding_vector, # Embedding já é List[float]
                 "pagina": domain_chunk.page_number,
                 "posicao": domain_chunk.position,
                 "metadados": json.dumps(domain_chunk.metadata) if domain_chunk.metadata else None # Garantir JSON para metadados
             })
             chunks_to_return.append(domain_chunk) # Adiciona o chunk original à lista

        try:
            # Usar INSERT ... ON CONFLICT (UPSERT) se o ID não for garantido único ou se for atualização
            # Se for sempre inserção nova (ID gerado pelo DB), um INSERT simples basta.
            # Assumindo INSERT simples por enquanto.
            # Se a tabela ChunkDB tiver um ID auto-incrementável, precisamos recuperá-los.

            # Usar a sintaxe pg_insert para retornar os IDs (ou todos os campos)
            stmt = pg_insert(ChunkDB).values(values_to_insert)
            # Adicionar cláusula RETURNING para obter os IDs (ou outros campos) gerados
            # Ajuste o nome 'id' se for diferente na sua classe ChunkDB
            stmt = stmt.returning(ChunkDB.id, ChunkDB.documento_id, ChunkDB.texto, ChunkDB.pagina, ChunkDB.posicao, ChunkDB.metadados)

            result = await self._session.execute(stmt)
            await self._session.commit()

            # Mapear resultados de volta para atualizar IDs nos Chunks de domínio
            inserted_rows = result.fetchall() # Fetchall para pegar todas as linhas retornadas
            if len(inserted_rows) != len(chunks_to_return):
                 logger.warning(f"Número de linhas retornadas ({len(inserted_rows)}) diferente do número de chunks enviados ({len(chunks_to_return)})")
                 # Pode precisar de lógica mais robusta para mapear de volta se a ordem não for garantida

            # Atualizar os IDs nos objetos Chunk que vamos retornar
            for i, row in enumerate(inserted_rows):
                 if i < len(chunks_to_return):
                     # row[0] deve ser o ID retornado
                     chunks_to_return[i].id = row[0] # Atualiza o ID no objeto de domínio

            logger.info(f"{len(inserted_rows)} chunks salvos em lote (com embeddings).")
            return chunks_to_return # Retorna os chunks originais, agora com IDs

        except Exception as e:
            logger.exception(f"Erro ao salvar chunks em lote com embeddings: {e}")
            await self._session.rollback()
            raise

    # --- Métodos find_* e delete_* (Manter como estão, eles operam sobre dados existentes) ---
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

    # --- Implementação de find_similar_chunks ---
    async def find_similar_chunks(
        self,
        embedding_vector: List[float],
        limit: int,
        filter_document_ids: Optional[List[int]] = None
    ) -> List[Tuple[Chunk, float]]:
        """ Encontra chunks semanticamente similares usando busca vetorial e retorna scores. """
        logger.debug(f"Executando find_similar_chunks com limite {limit} e filtro: {filter_document_ids}")
        try:
             # Escolher o operador de distância/similaridade
             # Ex: Cosseno (<=>), L2 (<->), Produto Interno (<#>)
             # Para Cosseno, score = 1 - distance. Para Produto Interno, score é o próprio resultado (se normalizado).
             distance_op = ChunkDB.embedding.cosine_distance(embedding_vector) # Exemplo com Cosseno
             # Se usar produto interno e quiser score maior = melhor: distance_op = (ChunkDB.embedding.max_inner_product(embedding_vector) * -1)

             stmt = select(ChunkDB, distance_op.label("distance")).order_by(distance_op).limit(limit)

             if filter_document_ids:
                 stmt = stmt.where(ChunkDB.documento_id.in_(filter_document_ids))

             results = await self._session.execute(stmt)
             db_chunks_with_distance = results.all() # Retorna tuplas (ChunkDB, distance)

             # Mapear para entidades de domínio E CALCULAR SCORE
             domain_chunks_with_score: List[Tuple[Chunk, float]] = []
             for db_chunk, distance in db_chunks_with_distance:
                 domain_chunk = self._map_db_to_domain(db_chunk)
                 if domain_chunk:
                     # Calcular score a partir da distância. Ex: para cosseno.
                     # Scores maiores indicam maior similaridade.
                     score = 1.0 - float(distance) # <-- MUDANÇA: Calcular score
                     # Garantir que score não seja negativo (pode acontecer com L2/outros)
                     score = max(0.0, score)
                     domain_chunks_with_score.append((domain_chunk, score)) # <-- MUDANÇA: Adicionar tupla

             logger.info(f"Busca vetorial encontrou {len(domain_chunks_with_score)} chunks similares com scores.")
             # Retorna a lista de tuplas (Chunk, score)
             return domain_chunks_with_score # <-- MUDANÇA: Retornar lista de tuplas

        except Exception as e:
             logger.exception(f"Erro durante a busca por similaridade de chunks: {e}")
             return [] # Retorna lista vazia em caso de erro

    async def find_by_keyword(self, query: str, limit: int, filter_document_ids: Optional[List[int]] = None) -> List[Tuple[Chunk, float]]:
        """ Encontra chunks baseados na relevância textual (keyword search) usando FTS. """
        logger.debug(f"Executando find_by_keyword para query: '{query}', limit: {limit}, filtro: {filter_document_ids}")
        if not query or not query.strip():
             logger.warning("Busca por keyword com query vazia.")
             return []
        try:
            # Usar a expressão indexada (to_tsvector) na query
            ts_vector_expression = func.to_tsvector('portuguese', ChunkDB.texto)
            # Usar plainto_tsquery para converter a query do usuário
            ts_query = func.plainto_tsquery('portuguese', query)
            # Usar ts_rank para calcular a relevância
            rank_function = func.ts_rank(ts_vector_expression, ts_query).label("rank")

            # Montar a query: SELECT chunk.*, rank WHERE expressao @@ query ORDER BY rank DESC LIMIT limit
            stmt = select(ChunkDB, rank_function).\
                   where(ts_vector_expression.op('@@')(ts_query)).\
                   order_by(rank_function.desc()).\
                   limit(limit)

            # Adicionar filtro de documento se fornecido
            if filter_document_ids:
                stmt = stmt.where(ChunkDB.documento_id.in_(filter_document_ids))

            results = await self._session.execute(stmt)
            db_chunks_with_rank = results.all() # Retorna tuplas (ChunkDB, rank)

            domain_chunks_with_score: List[Tuple[Chunk, float]] = []
            for db_chunk, rank_score in db_chunks_with_rank:
                domain_chunk = self._map_db_to_domain(db_chunk)
                if domain_chunk:
                    # O rank já é um score de relevância (maior é melhor)
                    # Normalizar para 0-1 pode ser útil para RRF, mas opcional
                    # score = float(rank_score) / (max_rank + epsilon) # Exemplo normalização
                    # Por enquanto, usar o rank diretamente como score
                    score = float(rank_score) if rank_score is not None else 0.0
                    domain_chunks_with_score.append((domain_chunk, score))

            logger.info(f"Busca por keyword encontrou {len(domain_chunks_with_score)} chunks.")
            return domain_chunks_with_score

        except Exception as e:
            # Log detalhado do erro SQL se possível
            sql_error_msg = str(e.__cause__) if hasattr(e, '__cause__') else str(e)
            logger.exception(f"Erro durante busca por keyword: {sql_error_msg}")
            # Verificar se o erro é por falta de configuração FTS
            if "function to_tsvector(unknown, character varying) does not exist" in sql_error_msg:
                 logger.error("Erro FTS: Função to_tsvector não encontrada ou extensão não habilitada no PostgreSQL?")
            elif "operator does not exist: tsvector @@ tsquery" in sql_error_msg:
                 logger.error("Erro FTS: Operador @@ não encontrado. Índice FTS ou extensão estão corretos?")
            return [] # Retornar vazio em caso de erro
