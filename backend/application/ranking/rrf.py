from typing import List, Tuple, Dict, Set
from domain.aggregates.document.chunk import Chunk
import logging

logger = logging.getLogger(__name__)

def reciprocal_rank_fusion(
    results_list: List[List[Tuple[Chunk, float]]],
    k: int = 60 # Parâmetro RRF, controla a importância de ranks mais baixos
) -> Tuple[List[Chunk], Dict[int, float]]:
    """
    Combina múltiplas listas de resultados de busca usando Reciprocal Rank Fusion (RRF).

    Args:
        results_list: Uma lista de listas de resultados. Cada lista interna
                      contém tuplas (Chunk, score), ordenada pelo score descendente.
        k: Parâmetro de ajuste do RRF (valor padrão comum é 60).

    Returns:
        Uma tupla contendo:
        - List[Chunk]: Lista de Chunks unificada e reordenada pelo score RRF (maior primeiro).
        - Dict[int, float]: Dicionário mapeando chunk_id para seu score RRF calculado.
                           Inclui apenas chunks que apareceram em pelo menos uma lista.
    """
    if not results_list:
        return [], {}

    rrf_scores: Dict[int, float] = {}
    all_chunks: Dict[int, Chunk] = {}
    logger.debug(f"Iniciando RRF com {len(results_list)} listas de resultados e k={k}")

    for results in results_list:
        if not results:
            continue
        for rank, (chunk, score) in enumerate(results):
            if chunk is None or chunk.id is None:
                logger.warning(f"Chunk inválido ou sem ID encontrado durante RRF: {chunk}")
                continue
            chunk_id = chunk.id
            if chunk_id not in all_chunks:
                all_chunks[chunk_id] = chunk
            rank_contribution = 1.0 / (k + (rank + 1))
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + rank_contribution

    sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)
    final_ranked_chunks: List[Chunk] = [all_chunks[cid] for cid in sorted_chunk_ids if cid in all_chunks]
    logger.info(f"RRF concluído. {len(final_ranked_chunks)} chunks únicos classificados.")

    return final_ranked_chunks, rrf_scores

# Adicionar __init__.py na pasta application/ranking se necessário para imports
