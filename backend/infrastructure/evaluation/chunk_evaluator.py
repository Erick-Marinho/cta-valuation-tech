import asyncio
import logging
from typing import List, Dict, Any

# Importar a Interface da Aplicação
from application.interfaces.chunker import ChunkQualityEvaluator

# Importar a função original (do novo local) ou reimplementar a lógica aqui
# Se a função original foi movida para semantic_chunker na infra:
try:
    from infrastructure.processors.chunkers.semantic_chunker import evaluate_chunk_quality
except ImportError:
    logger.warning("Função evaluate_chunk_quality não encontrada. Implementação básica será usada.")
    # Implementação placeholder se a original não for encontrada/movida
    def evaluate_chunk_quality(chunks: List[str], original_text: str) -> Dict[str, Any]:
         return {"avg_coherence": 0.0, "details": "Evaluation logic not implemented"}


logger = logging.getLogger(__name__)

class BasicChunkQualityEvaluator(ChunkQualityEvaluator):
    """ Implementação básica para avaliar qualidade de chunks. """

    async def evaluate(self, chunks: List[str], original_text: str) -> Dict[str, Any]:
        """ Avalia a qualidade dos chunks chamando a lógica subjacente. """
        if not chunks:
            return {}
        logger.info(f"Avaliando qualidade de {len(chunks)} chunks.")
        try:
            # Assumindo que evaluate_chunk_quality é síncrona
            def sync_evaluate():
                return evaluate_chunk_quality(chunks, original_text)

            quality_metrics = await asyncio.to_thread(sync_evaluate)
            logger.info(f"Métricas de qualidade dos chunks calculadas: {quality_metrics}")
            return quality_metrics
        except Exception as e:
            logger.exception(f"Erro ao avaliar qualidade dos chunks: {e}")
            # Retornar dicionário vazio ou métricas padrão em caso de erro
            return {"error": str(e)}
