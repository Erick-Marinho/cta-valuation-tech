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

# Consulta para obter o score de similaridade de um chunk específico
GET_SIMILARITY_SCORE_QUERY = """
SELECT 
    1 - (cv.embedding <=> %s::vector) as similarity_score
FROM 
    chunks_vetorizados cv
WHERE 
    cv.id = %s
"""

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
    
    # Iniciar span para rastrear a busca híbrida completa
    with tracer.start_as_current_span("realizar_busca_hibrida") as span:
        # Registrar parâmetros da busca
        span.set_attribute("query.text", query_text)
        span.set_attribute("query.embedding_size", len(query_embedding))
        span.set_attribute("search.limite", limite)
        span.set_attribute("search.alpha", alpha)
        
        if filtro_documentos:
            span.set_attribute("search.filter_docs_count", len(filtro_documentos))
        if strategy_filter:
            span.set_attribute("search.strategy_filter", strategy_filter)
        
        settings = get_settings()
        
        if threshold is None:
            threshold = settings.SEARCH_THRESHOLD
        span.set_attribute("search.threshold", threshold)
        
        try:
            # Construir cláusulas de filtro se necessário
            filter_clause = ""
            filter_params_vector = []
            filter_params_text = []
            where_conditions = []
            
            if filtro_documentos:
                placeholders = ', '.join(['%s'] * len(filtro_documentos))
                where_conditions.append(f"cv.documento_id IN ({placeholders})")
                filter_params_vector.extend(filtro_documentos)
                filter_params_text.extend(filtro_documentos)
                
            # Filtro por estratégia de chunking
            if strategy_filter:
                where_conditions.append("cv.metadados->>'chunking_strategy' = %s")
                filter_params_vector.append(strategy_filter)
                filter_params_text.append(strategy_filter)
            
            if filtro_metadados:
                # Construir condições JSONB para filtragem por metadados
                # Exemplo: WHERE cv.metadados @> '{"chave": "valor"}'::jsonb
                # Isso seria uma implementação mais complexa que exigiria
                # construção dinâmica de queries JSONB
                pass
            
            # Combinar condições em uma cláusula WHERE
            if where_conditions:
                filter_clause = "WHERE " + " AND ".join(where_conditions)
            
            # Parâmetros completos para as consultas
            vector_params = [query_embedding] + filter_params_vector + [query_embedding, 20]
            text_params = [query_text, query_text] + filter_params_text + [20]
            
            # Executar consulta vetorial
            vector_start_time = time.time()
            
            with tracer.start_as_current_span("busca_vetorial") as vector_span:
                vector_span.set_attribute("query.filter_clause", filter_clause)
                vector_query = VECTOR_SEARCH_QUERY.format(
                    filter_clause=filter_clause
                )
                vector_rows = execute_query(vector_query, vector_params)
                
            vector_elapsed = time.time() - vector_start_time
            record_retrieval_time(vector_elapsed, 'vector')  # Métrica Prometheus
            
            # Executar consulta textual
            text_start_time = time.time()
            
            with tracer.start_as_current_span("busca_textual") as text_span:
                text_filter_clause = " AND ".join(where_conditions) if where_conditions else ""
                text_query = TEXT_SEARCH_QUERY.format(
                    filter_clause=f"AND {text_filter_clause}" if text_filter_clause else ""
                )
                text_rows = execute_query(text_query, text_params)
            
            text_elapsed = time.time() - text_start_time
            record_retrieval_time(text_elapsed, 'text')  # Métrica Prometheus
            
            # Processar resultados
            process_start_time = time.time()
            
            with tracer.start_as_current_span("processar_resultados") as process_span:
                combined_results = {}
                
                # Adicionar resultados da busca vetorial
                for row in vector_rows:
                    chunk_id = row['id']
                    chunk = Chunk.from_db_row(row)
                    combined_results[chunk_id] = chunk
                
                # Adicionar ou atualizar resultados da busca textual
                for row in text_rows:
                    chunk_id = row['id']
                    text_score = float(row['text_score'])
                    
                    if chunk_id in combined_results:
                        # Atualizar texto score para chunks já encontrados
                        combined_results[chunk_id].text_score = text_score
                    else:
                        # Buscar score de similaridade para novos chunks
                        with tracer.start_as_current_span("get_similarity_score") as sim_span:
                            sim_span.set_attribute("chunk.id", chunk_id)
                            similarity_row = execute_query_single_result(
                                GET_SIMILARITY_SCORE_QUERY,
                                (query_embedding, chunk_id)
                            )
                            
                            similarity_score = 0.0
                            if similarity_row and 'similarity_score' in similarity_row:
                                similarity_score = float(similarity_row['similarity_score'])
                                sim_span.set_attribute("similarity_score", similarity_score)
                        
                        chunk = Chunk.from_db_row(row)
                        chunk.similarity_score = similarity_score
                        combined_results[chunk_id] = chunk
                        
                process_span.set_attribute("combined_results.count", len(combined_results))
                
                for chunk in combined_results.values():
                    record_retrieval_score(chunk.similarity_score, 'vector')
                    if hasattr(chunk, 'text_score') and chunk.text_score > 0:
                        record_retrieval_score(chunk.text_score, 'text')
                
                #Calcular scores combinados
                for chunk in combined_results.values():
                    # Normalizar text_score
                    norm_text_score = min(getattr(chunk, 'text_score', 0.0), 1.0) # Usar getattr com default
                    
                    # Combinar scores
                    chunk.combined_score = alpha * chunk.similarity_score + (1 - alpha) * norm_text_score
                    
                    # Registrar score combinado
                    record_retrieval_score(chunk.combined_score, 'hybrid')
                
                # Contar total de resultados antes do filtro de threshold
                total_resultados = len(combined_results)
                
                # Filtro de threshold    
                filtered_chunks = [chunk for chunk in combined_results.values()
                                if chunk.combined_score >= threshold]
                
                # Registrar impacto do threshold
                retained_count = len(filtered_chunks)
                filtered_count = total_resultados - retained_count
                if retained_count > 0:
                    record_threshold_filtering(action='retained', count=retained_count)
                if filtered_count > 0:
                    record_threshold_filtering(action='filtered', count=filtered_count)
                
                # Ordenar e limitar resultados
                sorted_chunks = sorted(
                    filtered_chunks, 
                    key=lambda x: x.combined_score, 
                    reverse=True
                )[:limite]
                    
                logger.info(f"Query text: '{query_text}'")
                logger.info(f"Resultados antes do filtro de threshold: {len(combined_results)}")
                logger.info(f"Threshold aplicado: {threshold}")
                logger.info(f"Resultados após filtro de threshold: {len(filtered_chunks)}")
                logger.info(f"Resultado variavel: {limite}")
                
                # Log detalhado para depuração
                for i, chunk in enumerate(sorted_chunks[:min(3, len(sorted_chunks))]):
                    chunking_strategy = chunk.metadados.get('chunking_strategy', 'desconhecida') if chunk.metadados else 'desconhecida'
                    logger.debug(
                        f"Top {i+1}: id={chunk.id}, score={chunk.combined_score:.4f}, "
                        f"estratégia={chunking_strategy}, "
                        f"texto={chunk.texto[:50]}..."
                    )
                    
                process_elapsed = time.time() - process_start_time
                record_retrieval_time(process_elapsed, 'process')  # Métrica Prometheus
            
                # Registrar total de documentos recuperados
                record_documents_retrieved(len(sorted_chunks))
            
                # Registrar tempo total
                total_elapsed = time.time() - start_time_total
                record_retrieval_time(total_elapsed, 'total')  # Métrica Prometheus
                
                return sorted_chunks
                
        except Exception as e:
            # Registrar erro no span
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, f"Erro: {e}"))
            
            logger.error(f"Erro na busca híbrida avançada: {e}")
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
    # Iniciar span para rastrear o reranking
    with tracer.start_as_current_span("rerank_results") as span:
        span.set_attribute("chunks.count", len(chunks) if chunks else 0)
        span.set_attribute("query.text", query_text)
        
        # Implementação simplificada que poderia ser expandida
        # para usar modelos externos de reranking mais sofisticados
        
        if not chunks:
            span.set_attribute("results.empty", True)
            return []
        
        # Por enquanto, apenas refina os scores com base em heurísticas simples
        for chunk in chunks:
            with tracer.start_as_current_span("apply_heuristics") as heuristic_span:
                heuristic_span.set_attribute("chunk.id", chunk.id)
                heuristic_span.set_attribute("original_score", chunk.combined_score)
                
                # Heurística 1: Valorizar documentos onde o termo de busca aparece primeiro
                position_boost = 0.0
                if query_text.lower() in chunk.texto.lower():
                    position = chunk.texto.lower().find(query_text.lower())
                    # Quanto mais próximo do início, maior o boost (máximo 0.05)
                    position_boost = max(0, 0.05 * (1 - position / len(chunk.texto)))
                    heuristic_span.set_attribute("position_boost", position_boost)
                
                # Heurística 2: Valorizar chunks mais concisos (dentro de limites razoáveis)
                length_penalty = 0.0
                ideal_length = 500  # Tamanho ideal em caracteres
                actual_length = len(chunk.texto)
                if actual_length > ideal_length * 3:
                    # Penalizar chunks muito longos
                    length_penalty = min(0.03, (actual_length - ideal_length * 3) / 10000)
                    heuristic_span.set_attribute("length_penalty", length_penalty)
                
                # 3. Boost baseado na estratégia de chunking (preferência contextual)
                strategy_boost = 0.0
                if chunk.metadados and 'chunking_strategy' in chunk.metadados:
                    strategy = chunk.metadados['chunking_strategy']
                    heuristic_span.set_attribute("chunking_strategy", strategy)
                    
                    # Tipo de consulta baseado no comprimento e estrutura
                    query_words = query_text.split()
                    is_specific_query = len(query_words) > 5 or '?' in query_text
                    heuristic_span.set_attribute("is_specific_query", is_specific_query)
                    
                    if is_specific_query and strategy == "header_based":
                        # Consultas específicas funcionam melhor com chunks baseados em cabeçalhos
                        strategy_boost = 0.03
                    elif not is_specific_query and strategy == "paragraph":
                        # Consultas simples funcionam bem com chunks de parágrafo
                        strategy_boost = 0.02
                    elif strategy == "hybrid":
                        # Híbrido é geralmente um bom meio termo
                        strategy_boost = 0.01
                    
                    heuristic_span.set_attribute("strategy_boost", strategy_boost)
                        
                # 4. Boost baseado na qualidade do chunk
                quality_boost = 0.0
                if chunk.metadados and 'chunk_quality' in chunk.metadados:
                    # Qualidade é um valor entre 0 e 1
                    quality = float(chunk.metadados['chunk_quality'])
                    quality_boost = quality * 0.04  # Máximo de 4%
                    heuristic_span.set_attribute("quality_boost", quality_boost)
                
                # Aplicar todos os ajustes
                total_adjustment = position_boost + strategy_boost + quality_boost - length_penalty
                heuristic_span.set_attribute("total_adjustment", total_adjustment)
                
                # Registrar score original e ajustado
                original_score = chunk.combined_score
                chunk.combined_score = chunk.combined_score * (1 + total_adjustment)
                heuristic_span.set_attribute("adjusted_score", chunk.combined_score)
                
                record_retrieval_score(chunk.combined_score, 'reranked')
        
        # Reordenar com base nos scores ajustados
        result = sorted(chunks, key=lambda x: x.combined_score, reverse=True)
        
        # Registrar métricas no span principal
        if result:
            span.set_attribute("results.top_score", result[0].combined_score)
        
        elapsed_time = time.time() - start_time
        record_retrieval_time(elapsed_time, 'rerank')  # Métrica Prometheus

        return result
