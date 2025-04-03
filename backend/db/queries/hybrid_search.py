"""
Queries especializadas para busca híbrida (combinação de busca vetorial e textual).
"""
import time
import logging
from typing import List, Dict, Any, Tuple, Optional
from ..connection import execute_query, execute_query_single_result
from ..models.chunk import Chunk
from core.config import get_settings
from utils.logging import track_timing
from utils.metrics_prometheus import record_retrieval_time, record_documents_retrieved, record_retrieval_score, record_threshold_filtering
# Importar telemetria
from utils.telemetry import get_tracer
from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode
from opentelemetry.semconv.trace import SpanAttributes as SemanticSpanAttributes

logger = logging.getLogger(__name__)
# Obter tracer para este módulo
tracer = get_tracer(__name__)

start_time = time.time()

# Consulta para busca vetorial com metadados opcionais
VECTOR_SEARCH_QUERY = """
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
{filter_clause}
ORDER BY 
    cv.embedding <=> %s::vector
LIMIT %s
"""

# Consulta para busca textual com metadados opcionais
TEXT_SEARCH_QUERY = """
SELECT 
    cv.id, 
    cv.documento_id, 
    cv.texto, 
    cv.pagina, 
    cv.posicao, 
    cv.metadados,
    ts_rank_cd(to_tsvector('portuguese', cv.texto), plainto_tsquery('portuguese', lower(%s))) as text_score,
    (SELECT nome_arquivo FROM documentos_originais WHERE id = cv.documento_id) as arquivo_origem
FROM 
    chunks_vetorizados cv
WHERE 
    to_tsvector('portuguese', lower(cv.texto)) @@ plainto_tsquery('portuguese', lower(%s))
    {filter_clause}
ORDER BY 
    text_score DESC
LIMIT %s
"""

# Consulta para obter o score de similaridade de um chunk específico (Template)
# Usaremos esta forma para atributos, evitando expor dados diretamente
GET_SIMILARITY_SCORE_QUERY_TEMPLATE = "SELECT 1 - (embedding <=> %s::vector) as score FROM chunks_vetorizados WHERE id = %s"

@track_timing
def realizar_busca_hibrida(query_text: str, query_embedding: List[float], 
                        limite: int = 3, alpha: float = 0.7,
                        filtro_documentos: List[int] = None,
                        filtro_metadados: Dict[str, Any] = None,
                        threshold: float = None,
                        strategy_filter: str = None,
                        ) -> List[Chunk]:
    """
    Realiza uma busca híbrida avançada combinando busca vetorial e textual,
    com opções de filtragem por IDs de documentos e metadados.
    
    Args:
        query_text (str): Texto da query
        query_embedding (list): Embedding da query
        limite (int): Número máximo de resultados
        alpha (float): Peso para busca vetorial (0.0 - 1.0)
        filtro_documentos (list): Lista opcional de IDs de documentos para filtrar
        filtro_metadados (dict): Filtros opcionais de metadados
        strategy_filter (str): Filtrar por estratégia de chunking específica
        
    Returns:
        list: Lista de chunks ordenados por score combinado
    """
    
    start_time_total = time.time()
    
    # Refinar span principal da busca híbrida
    with tracer.start_as_current_span(
        "db.hybrid_search", # Nome mais indicativo da camada
        kind=SpanKind.INTERNAL # Orquestra chamadas DB, mas é interno ao serviço
    ) as span:
        # Atributos gerais da operação
        span.set_attribute("db.system", "postgresql") # Sistema de DB
        span.set_attribute("app.search.query_text", query_text) # Usar prefixo 'app' para dados da aplicação
        span.set_attribute("app.search.embedding_provided", bool(query_embedding))
        span.set_attribute("app.search.limit", limite)
        span.set_attribute("app.search.alpha", alpha)
        span.set_attribute("app.search.threshold", threshold or get_settings().SEARCH_THRESHOLD)
        if filtro_documentos:
            span.set_attribute("app.search.filter_docs_count", len(filtro_documentos))
        if strategy_filter:
            span.set_attribute("app.search.strategy_filter", strategy_filter)
        # if filtro_metadados: # Adicionar se implementado
        #    span.set_attribute("app.search.filter_metadata_keys", str(list(filtro_metadados.keys())))

        settings = get_settings() # Mover para dentro se threshold for None
        effective_threshold = threshold if threshold is not None else settings.SEARCH_THRESHOLD
        span.set_attribute("app.search.effective_threshold", effective_threshold) # Registrar threshold efetivo

        try:
            # Construção de cláusulas de filtro (manter lógica)
            filter_clause_sql = ""
            filter_params_vector = []
            filter_params_text = []
            where_conditions = []

            if filtro_documentos:
                placeholders = ', '.join(['%s'] * len(filtro_documentos))
                where_conditions.append(f"cv.documento_id IN ({placeholders})")
                filter_params_vector.extend(filtro_documentos)
                filter_params_text.extend(filtro_documentos)

            if strategy_filter:
                where_conditions.append("cv.metadados->>'chunking_strategy' = %s")
                filter_params_vector.append(strategy_filter)
                filter_params_text.append(strategy_filter)

            # Combinar condições
            if where_conditions:
                filter_clause_sql = "WHERE " + " AND ".join(where_conditions)
            span.set_attribute("db.sql.filter_clause", filter_clause_sql) # Adicionar cláusula ao span

            # Limite maior para busca inicial
            initial_limit = limite * 3 # Buscar mais para processamento posterior
            span.set_attribute("db.sql.initial_limit", initial_limit)

            vector_params = [query_embedding] + filter_params_vector + [query_embedding, initial_limit]
            text_params = [query_text, query_text] + filter_params_text + [initial_limit]

            # Instrumentar chamada da busca vetorial
            vector_start_time = time.time()
            vector_rows = []
            with tracer.start_as_current_span(
                "db.vector_search", # Nome específico da operação
                kind=SpanKind.CLIENT # Representa uma chamada ao DB
            ) as vector_span:
                vector_query_formatted = VECTOR_SEARCH_QUERY.format(filter_clause=filter_clause_sql)
                # Adicionar atributos semânticos do DB
                vector_span.set_attribute(SemanticSpanAttributes.DB_SYSTEM, "postgresql")
                vector_span.set_attribute(SemanticSpanAttributes.DB_OPERATION, "SELECT vector_similarity")
                vector_span.set_attribute(SemanticSpanAttributes.DB_STATEMENT, VECTOR_SEARCH_QUERY) # Query template
                vector_span.set_attribute(SemanticSpanAttributes.DB_SQL_TABLE, "chunks_vetorizados")
                vector_span.set_attribute("db.sql.params_count", len(vector_params))
                vector_span.set_attribute("db.sql.limit", initial_limit)

                try:
                    vector_rows = execute_query(vector_query_formatted, vector_params)
                    vector_span.set_attribute("db.result_rows", len(vector_rows))
                    vector_span.set_status(Status(StatusCode.OK))
                except Exception as db_exc:
                    vector_span.record_exception(db_exc)
                    vector_span.set_status(Status(StatusCode.ERROR, description=str(db_exc)))
                    vector_span.set_attribute("error.type", type(db_exc).__name__)
                    raise # Re-lançar para ser pego pelo try/except externo

            vector_elapsed = time.time() - vector_start_time
            record_retrieval_time(vector_elapsed, 'vector') # Métrica Prometheus

            # Instrumentar chamada da busca textual
            text_start_time = time.time()
            text_rows = []
            with tracer.start_as_current_span(
                 "db.text_search",
                 kind=SpanKind.CLIENT
            ) as text_span:
                 text_filter_clause_sql = f"AND {filter_clause_sql}" if filter_clause_sql else "" # Ajuste da lógica original
                 text_query_formatted = TEXT_SEARCH_QUERY.format(filter_clause=text_filter_clause_sql) # Usar versão formatada da cláusula
                 # Adicionar atributos semânticos do DB
                 text_span.set_attribute(SemanticSpanAttributes.DB_SYSTEM, "postgresql")
                 text_span.set_attribute(SemanticSpanAttributes.DB_OPERATION, "SELECT text_rank")
                 text_span.set_attribute(SemanticSpanAttributes.DB_STATEMENT, TEXT_SEARCH_QUERY) # Query template
                 text_span.set_attribute(SemanticSpanAttributes.DB_SQL_TABLE, "chunks_vetorizados")
                 text_span.set_attribute("db.sql.params_count", len(text_params))
                 text_span.set_attribute("db.sql.limit", initial_limit)

                 try:
                    text_rows = execute_query(text_query_formatted, text_params)
                    text_span.set_attribute("db.result_rows", len(text_rows))
                    text_span.set_status(Status(StatusCode.OK))
                 except Exception as db_exc:
                    text_span.record_exception(db_exc)
                    text_span.set_status(Status(StatusCode.ERROR, description=str(db_exc)))
                    text_span.set_attribute("error.type", type(db_exc).__name__)
                    raise # Re-lançar

            text_elapsed = time.time() - text_start_time
            record_retrieval_time(text_elapsed, 'text') # Métrica Prometheus

            # Refinar span de processamento e adicionar span para get_similarity_score
            process_start_time = time.time()
            with tracer.start_as_current_span(
                "db.process_hybrid_results",
                kind=SpanKind.INTERNAL
            ) as process_span:
                combined_results: Dict[int, Chunk] = {} # Tipagem

                # Adicionar resultados vetoriais
                for row in vector_rows:
                    chunk_id = row['id']
                    # Idealmente, Chunk.from_db_row não faria I/O, mas se fizer, precisa de tracing lá
                    chunk = Chunk.from_db_row(row)
                    combined_results[chunk_id] = chunk
                process_span.set_attribute("results.vector_count", len(vector_rows))

                # Adicionar/atualizar resultados textuais
                new_chunks_from_text = 0
                similarity_lookup_count = 0
                for row in text_rows:
                    chunk_id = row['id']
                    text_score = float(row['text_score']) if row.get('text_score') is not None else 0.0

                    if chunk_id in combined_results:
                        combined_results[chunk_id].text_score = text_score
                    else:
                        new_chunks_from_text += 1
                        similarity_score = 0.0
                        # Instrumentar busca de similaridade para chunks só textuais
                        similarity_lookup_start = time.time()
                        with tracer.start_as_current_span(
                             "db.get_similarity_for_text_chunk",
                             kind=SpanKind.CLIENT
                        ) as sim_span:
                            sim_span.set_attribute("app.chunk_id", chunk_id) # ID do chunk buscado
                            sim_span.set_attribute(SemanticSpanAttributes.DB_SYSTEM, "postgresql")
                            sim_span.set_attribute(SemanticSpanAttributes.DB_OPERATION, "SELECT vector_similarity")
                            sim_span.set_attribute(SemanticSpanAttributes.DB_STATEMENT, GET_SIMILARITY_SCORE_QUERY_TEMPLATE) # Usar template
                            sim_span.set_attribute(SemanticSpanAttributes.DB_SQL_TABLE, "chunks_vetorizados")

                            try:
                                similarity_row = execute_query_single_result(
                                    GET_SIMILARITY_SCORE_QUERY_TEMPLATE,
                                    (query_embedding, chunk_id)
                                )
                                similarity_lookup_count += 1
                                if similarity_row and 'similarity_score' in similarity_row:
                                    similarity_score = float(similarity_row['similarity_score'])
                                sim_span.set_attribute("db.result_score", similarity_score)
                                sim_span.set_status(Status(StatusCode.OK))
                            except Exception as db_exc:
                                sim_span.record_exception(db_exc)
                                sim_span.set_status(Status(StatusCode.ERROR, description=str(db_exc)))
                                sim_span.set_attribute("error.type", type(db_exc).__name__)
                                # Não relançar aqui, continuar com score 0.0

                        chunk = Chunk.from_db_row(row)
                        chunk.similarity_score = similarity_score
                        combined_results[chunk_id] = chunk

                process_span.set_attribute("results.text_count", len(text_rows))
                process_span.set_attribute("results.new_chunks_from_text", new_chunks_from_text)
                process_span.set_attribute("results.similarity_lookups", similarity_lookup_count)
                process_span.set_attribute("results.combined_initial_count", len(combined_results))

                # Registrar métricas de score (manter)
                for chunk in combined_results.values():
                    record_retrieval_score(chunk.similarity_score, 'vector')
                    if hasattr(chunk, 'text_score') and chunk.text_score > 0:
                        record_retrieval_score(chunk.text_score, 'text')
                
                # Calcular scores combinados (manter lógica)
                for chunk in combined_results.values():
                    # Normalizar text_score
                    norm_text_score = min(getattr(chunk, 'text_score', 0.0), 1.0) # Usar getattr com default
                    
                    # Combinar scores
                    chunk.combined_score = alpha * chunk.similarity_score + (1 - alpha) * norm_text_score
                    
                    # Registrar score combinado
                    record_retrieval_score(chunk.combined_score, 'hybrid')
                
                # Filtro de threshold (manter lógica)
                total_resultados_before_threshold = len(combined_results)
                filtered_chunks = [chunk for chunk in combined_results.values() if chunk.combined_score >= effective_threshold]
                retained_count = len(filtered_chunks)
                filtered_count = total_resultados_before_threshold - retained_count
                process_span.set_attribute("results.before_threshold_count", total_resultados_before_threshold)
                process_span.set_attribute("results.after_threshold_count", retained_count)
                process_span.set_attribute("results.filtered_by_threshold_count", filtered_count)
                # Registrar métricas Prometheus de threshold (manter)
                if retained_count > 0:
                    record_threshold_filtering(action='retained', count=retained_count)
                if filtered_count > 0:
                    record_threshold_filtering(action='filtered', count=filtered_count)
                
                # Ordenar e limitar (manter lógica)
                sorted_chunks = sorted(filtered_chunks, key=lambda x: x.combined_score, reverse=True)[:limite]
                process_span.set_attribute("results.final_count", len(sorted_chunks))
                if sorted_chunks:
                    process_span.set_attribute("results.top_score", sorted_chunks[0].combined_score)
                    process_span.set_attribute("results.lowest_score", sorted_chunks[-1].combined_score)

                process_elapsed = time.time() - process_start_time
                record_retrieval_time(process_elapsed, 'process') # Métrica Prometheus
                process_span.set_attribute("duration_ms", int(process_elapsed * 1000))
                process_span.set_status(Status(StatusCode.OK))


            # Registrar métricas finais (manter)
            record_documents_retrieved(len(sorted_chunks))
            total_elapsed = time.time() - start_time_total
            record_retrieval_time(total_elapsed, 'total') # Métrica Prometheus

            # Adicionar atributos finais ao span principal
            span.set_attribute("results.final_count", len(sorted_chunks))
            span.set_attribute("duration_ms", int(total_elapsed * 1000))
            span.set_status(Status(StatusCode.OK)) # Marcar OK no span principal

            return sorted_chunks

        except Exception as e:
            total_elapsed = time.time() - start_time_total # Calcular tempo mesmo em erro
            logger.error(f"Erro na busca híbrida: {e}", exc_info=True)
            # Registrar erro no span principal
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, description=str(e)))
            span.set_attribute("error.type", type(e).__name__)
            span.set_attribute("duration_ms", int(total_elapsed * 1000))

            return []


def rerank_results(chunks: List[Chunk], query_text: str) -> List[Chunk]:
    """
    Aplica uma etapa de reranking aos resultados para melhorar a relevância.
    Esta função poderia ser expandida para usar modelos de reranking mais avançados.
    
    Args:
        chunks (list): Lista de chunks a serem reordenados
        query_text (str): Texto da consulta original
        
    Returns:
        list: Lista de chunks reordenados
    """
    
    start_time = time.time()
    # Refinar span principal de reranking
    with tracer.start_as_current_span(
        "db.rerank_results", # Manter prefixo db? Ou app? Talvez app.rerank_results
        kind=SpanKind.INTERNAL # É processamento interno
    ) as span:
        initial_count = len(chunks)
        span.set_attribute("app.rerank.initial_count", initial_count)
        span.set_attribute("app.rerank.query_text", query_text)

        if not chunks:
            span.set_attribute("app.rerank.final_count", 0)
            span.set_status(Status(StatusCode.OK, "Lista de chunks vazia."))
            return []

        # Refinar span de heurísticas (se mantido)
        # Considerar remover este span interno se for muito granular/rápido
        for chunk in chunks:
             with tracer.start_as_current_span("db.rerank_apply_heuristics") as heuristic_span:
                heuristic_span.set_attribute("app.chunk_id", chunk.id)
                original_score = chunk.combined_score
                heuristic_span.set_attribute("app.rerank.original_score", original_score)

                # Lógica de heurísticas (manter)
                # ... (código das heurísticas: position_boost, length_penalty, strategy_boost, quality_boost) ...
                # Adicionar atributos para cada boost/penalty calculado ao heuristic_span
                # heuristic_span.set_attribute("app.rerank.heuristic.position_boost", position_boost)
                # ... etc ...
                position_boost = 0.0
                if query_text.lower() in chunk.texto.lower():
                    position = chunk.texto.lower().find(query_text.lower())
                    # Quanto mais próximo do início, maior o boost (máximo 0.05)
                    position_boost = max(0, 0.05 * (1 - position / len(chunk.texto)))
                    heuristic_span.set_attribute("app.rerank.heuristic.position_boost", position_boost)
                
                length_penalty = 0.0
                ideal_length = 500  # Tamanho ideal em caracteres
                actual_length = len(chunk.texto)
                if actual_length > ideal_length * 3:
                    # Penalizar chunks muito longos
                    length_penalty = min(0.03, (actual_length - ideal_length * 3) / 10000)
                    heuristic_span.set_attribute("app.rerank.heuristic.length_penalty", length_penalty)
                
                # 3. Boost baseado na estratégia de chunking (preferência contextual)
                strategy_boost = 0.0
                if chunk.metadados and 'chunking_strategy' in chunk.metadados:
                    strategy = chunk.metadados['chunking_strategy']
                    heuristic_span.set_attribute("app.rerank.heuristic.chunking_strategy", strategy)
                    
                    # Tipo de consulta baseado no comprimento e estrutura
                    query_words = query_text.split()
                    is_specific_query = len(query_words) > 5 or '?' in query_text
                    heuristic_span.set_attribute("app.rerank.heuristic.is_specific_query", is_specific_query)
                    
                    if is_specific_query and strategy == "header_based":
                        # Consultas específicas funcionam melhor com chunks baseados em cabeçalhos
                        strategy_boost = 0.03
                    elif not is_specific_query and strategy == "paragraph":
                        # Consultas simples funcionam bem com chunks de parágrafo
                        strategy_boost = 0.02
                    elif strategy == "hybrid":
                        # Híbrido é geralmente um bom meio termo
                        strategy_boost = 0.01
                    
                    heuristic_span.set_attribute("app.rerank.heuristic.strategy_boost", strategy_boost)
                        
                # 4. Boost baseado na qualidade do chunk
                quality_boost = 0.0
                if chunk.metadados and 'chunk_quality' in chunk.metadados:
                    # Qualidade é um valor entre 0 e 1
                    quality = float(chunk.metadados['chunk_quality'])
                    quality_boost = quality * 0.04  # Máximo de 4%
                    heuristic_span.set_attribute("app.rerank.heuristic.quality_boost", quality_boost)
                
                # Aplicar todos os ajustes
                total_adjustment = position_boost + strategy_boost + quality_boost - length_penalty
                chunk.combined_score = original_score * (1 + total_adjustment)

                heuristic_span.set_attribute("app.rerank.total_adjustment", total_adjustment)
                heuristic_span.set_attribute("app.rerank.adjusted_score", chunk.combined_score)
                heuristic_span.set_status(Status(StatusCode.OK))

             # Registrar métrica Prometheus (manter)
             record_retrieval_score(chunk.combined_score, 'reranked')

        # Reordenar (manter)
        result = sorted(chunks, key=lambda x: x.combined_score, reverse=True)

        elapsed_time = time.time() - start_time
        record_retrieval_time(elapsed_time, 'rerank') # Métrica Prometheus

        # Atributos finais do span principal rerank
        span.set_attribute("app.rerank.final_count", len(result))
        if result:
            span.set_attribute("app.rerank.top_score", result[0].combined_score)
            span.set_attribute("app.rerank.lowest_score", result[-1].combined_score)
        span.set_attribute("duration_ms", int(elapsed_time * 1000))
        span.set_status(Status(StatusCode.OK))

        return result
