"""
Queries especializadas para busca híbrida (combinação de busca vetorial e textual).
"""
import logging
from typing import List, Dict, Any, Tuple
from ..connection import execute_query, execute_query_single_result
from ..models.chunk import Chunk
from core.config import get_settings

logger = logging.getLogger(__name__)

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
    ts_rank_cd(to_tsvector('portuguese', cv.texto), plainto_tsquery('portuguese', %s)) as text_score,
    (SELECT nome_arquivo FROM documentos_originais WHERE id = cv.documento_id) as arquivo_origem
FROM 
    chunks_vetorizados cv
WHERE 
    to_tsvector('portuguese', cv.texto) @@ plainto_tsquery('portuguese', %s)
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

def realizar_busca_hibrida(query_text: str, query_embedding: List[float], 
                         limite: int = 5, alpha: float = 0.7,
                         filtro_documentos: List[int] = None,
                         filtro_metadados: Dict[str, Any] = None,
                         threshold: float = None,
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
        
    Returns:
        list: Lista de chunks ordenados por score combinado
    """
    
    settings = get_settings()
    if threshold is None:
      threshold = settings.SEARCH_THRESHOLD
    
    try:
        # Construir cláusulas de filtro se necessário
        filter_clause = ""
        filter_params_vector = []
        filter_params_text = []
        
        if filtro_documentos:
            placeholders = ', '.join(['%s'] * len(filtro_documentos))
            filter_clause += f"WHERE cv.documento_id IN ({placeholders})"
            filter_params_vector.extend(filtro_documentos)
            filter_params_text.extend(filtro_documentos)
        
        if filtro_metadados:
            # Construir condições JSONB para filtragem por metadados
            # Exemplo: WHERE cv.metadados @> '{"chave": "valor"}'::jsonb
            # Isso seria uma implementação mais complexa que exigiria
            # construção dinâmica de queries JSONB
            pass
        
        # Parâmetros completos para as consultas
        vector_params = [query_embedding] + filter_params_vector + [query_embedding, 20]
        text_params = [query_text, query_text] + filter_params_text + [20]
        
        # Executar consulta vetorial
        vector_query = VECTOR_SEARCH_QUERY.format(
            filter_clause="WHERE " + filter_clause[6:] if filter_clause.startswith("WHERE ") else filter_clause
        )
        vector_rows = execute_query(vector_query, vector_params)
        
        # Executar consulta textual
        text_query = TEXT_SEARCH_QUERY.format(
            filter_clause="AND " + filter_clause[6:] if filter_clause.startswith("WHERE ") else ""
        )
        text_rows = execute_query(text_query, text_params)
        
        # Processar resultados
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
                similarity_row = execute_query_single_result(
                    GET_SIMILARITY_SCORE_QUERY,
                    (query_embedding, chunk_id)
                )
                
                similarity_score = 0.0
                if similarity_row and 'similarity_score' in similarity_row:
                    similarity_score = float(similarity_row['similarity_score'])
                
                chunk = Chunk.from_db_row(row)
                chunk.similarity_score = similarity_score
                combined_results[chunk_id] = chunk
        
        #Calcular scores combinados
        for chunk in combined_results.values():
            # Normalizar text_score
            norm_text_score = min(chunk.text_score, 1.0)
            
        #     # Combinar scores
            chunk.combined_score = alpha * chunk.similarity_score + (1 - alpha) * norm_text_score
        
        # Filtro de threshold    
        filtered_chunks = [chunk for chunk in combined_results.values()
                           if chunk.combined_score >= threshold]    
        
        # Ordenar e limitar resultados
        sorted_chunks = sorted(
            filtered_chunks, 
            key=lambda x: x.combined_score, 
            reverse=True
        )[:limite]
        
        # Logar informações sobre a busca para depuração
        logger.debug(f"Busca híbrida por '{query_text}' retornou {len(sorted_chunks)} resultados")
        for i, chunk in enumerate(sorted_chunks):
            logger.debug(f"Resultado {i+1}: id={chunk.id}, score={chunk.combined_score:.4f}, "
                         f"arquivo={chunk.arquivo_origem}")
        
        return sorted_chunks
        
    except Exception as e:
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
    # Implementação simplificada que poderia ser expandida
    # para usar modelos externos de reranking mais sofisticados
    
    # Por enquanto, apenas refina os scores com base em heurísticas simples
    for chunk in chunks:
        # Heurística 1: Valorizar documentos onde o termo de busca aparece primeiro
        position_boost = 0.0
        if query_text.lower() in chunk.texto.lower():
            position = chunk.texto.lower().find(query_text.lower())
            # Quanto mais próximo do início, maior o boost (máximo 0.05)
            position_boost = max(0, 0.05 * (1 - position / len(chunk.texto)))
        
        # Heurística 2: Valorizar chunks mais concisos (dentro de limites razoáveis)
        length_penalty = 0.0
        ideal_length = 500  # Tamanho ideal em caracteres
        actual_length = len(chunk.texto)
        if actual_length > ideal_length * 2:
            # Penalizar chunks muito longos
            length_penalty = min(0.03, (actual_length - ideal_length * 2) / 10000)
        
        # Aplicar ajustes ao score
        chunk.combined_score = chunk.combined_score + position_boost - length_penalty
    
    # Reordenar com base nos scores ajustados
    return sorted(chunks, key=lambda x: x.combined_score, reverse=True)