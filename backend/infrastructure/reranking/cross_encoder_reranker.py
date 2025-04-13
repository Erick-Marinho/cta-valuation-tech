import logging
import time
import asyncio
from typing import List, Tuple, Optional

# Imports da Nova Estrutura
from application.interfaces.reranker import ReRanker
from domain.aggregates.document.chunk import Chunk
from config.config import get_settings # Para obter configurações, como nome do modelo

# Importar CrossEncoder
from sentence_transformers import CrossEncoder

# Telemetria/Métricas (Opcional, mas recomendado)
# from utils.telemetry import get_tracer # <-- Linha antiga comentada/removida
from infrastructure.telemetry.opentelemetry import get_tracer # <-- Linha corrigida
from opentelemetry import trace
from opentelemetry.trace import SpanKind
# from utils.metrics_prometheus import record_rerank_time # <-- Manter comentado ou corrigir se for usar
# from infrastructure.metrics.prometheus.metrics_prometheus import record_rerank_time # Exemplo de correção se for usar

logger = logging.getLogger(__name__)

class CrossEncoderReRanker(ReRanker):
    """
    Implementação do ReRanker usando um modelo Cross-Encoder da sentence-transformers.
    """

    def __init__(self, model_name: Optional[str] = None, device: Optional[str] = None):
        """
        Inicializa o re-ranker Cross-Encoder.

        Args:
            model_name: Nome do modelo Cross-Encoder (ex: 'cross-encoder/ms-marco-MiniLM-L-6-v2').
                        Se None, tentará obter de settings.RERANKER_MODEL.
            device: Dispositivo para carregar o modelo ('cpu', 'cuda', etc.).
                    Se None, tentará obter de settings ou auto-detectar.
        """
        self.tracer = get_tracer(__name__)
        with self.tracer.start_as_current_span("cross_encoder_reranker.__init__") as span:
            self.settings = get_settings()
            # Definir modelo e dispositivo
            _model_name = model_name or getattr(self.settings, 'RERANKER_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
            _device = device or ('cuda' if getattr(self.settings, 'USE_GPU', False) else 'cpu')

            span.set_attribute("reranker.model_name", _model_name)
            span.set_attribute("reranker.device", _device)
            logger.info(f"Inicializando CrossEncoderReRanker com modelo: {_model_name} no dispositivo: {_device}")

            try:
                start_load = time.time()
                # max_length pode ser ajustado conforme necessidade e capacidade do modelo/memória
                self.model = CrossEncoder(_model_name, device=_device, max_length=512)
                load_time = time.time() - start_load
                logger.info(f"Modelo CrossEncoder '{_model_name}' carregado em {load_time:.2f}s.")
                span.set_attribute("reranker.load_time_ms", int(load_time * 1000))
                span.set_status(trace.StatusCode.OK)
            except Exception as e:
                logger.error(f"Falha ao carregar modelo CrossEncoder '{_model_name}': {e}", exc_info=True)
                span.record_exception(e)
                span.set_status(trace.StatusCode.ERROR, description=str(e))
                raise RuntimeError(f"Falha ao inicializar CrossEncoderReRanker: {e}") from e

    async def rerank(
        self,
        query: str,
        chunks: List[Chunk]
    ) -> List[Tuple[Chunk, float]]:
        """
        Reordena chunks usando o modelo Cross-Encoder carregado.

        Retorna a lista de chunks ordenada pelo score do Cross-Encoder (maior primeiro).
        """
        with self.tracer.start_as_current_span("cross_encoder_reranker.rerank") as span:
            span.set_attribute("reranker.input_chunks_count", len(chunks))
            span.set_attribute("reranker.query_length", len(query))

            if not chunks:
                logger.warning("Tentativa de rerank com lista de chunks vazia.")
                span.set_status(trace.StatusCode.OK, "Lista de chunks vazia.")
                return [(chunk, 0.0) for chunk in chunks]
            if not query:
                 logger.warning("Tentativa de rerank com query vazia.")
                 span.set_status(trace.StatusCode.OK, "Query vazia.")
                 return [(chunk, 0.0) for chunk in chunks]

            try:
                start_predict = time.time()

                # Formatar pares [query, chunk_text] para o modelo
                model_input: List[Tuple[str, str]] = [(query, chunk.text) for chunk in chunks]

                # Função síncrona para a predição
                def sync_predict():
                    # O método predict retorna scores numéricos (quanto maior, mais relevante)
                    return self.model.predict(model_input, show_progress_bar=False) # Desativar barra de progresso

                # Executar predição em thread separada
                scores = await asyncio.to_thread(sync_predict)

                predict_time = time.time() - start_predict
                span.set_attribute("reranker.predict_time_ms", int(predict_time * 1000))
                # record_rerank_time(predict_time) # Adicionar métrica se existir (e se import foi corrigido/descomentado)

                if len(scores) != len(chunks):
                     logger.error(f"Número de scores ({len(scores)}) diferente do número de chunks ({len(chunks)})!")
                     span.set_status(trace.StatusCode.ERROR, "Mismatch entre scores e chunks.")
                     # Retornar lista de tuplas com score 0 ou erro? Score 0.
                     return [(chunk, 0.0) for chunk in chunks]

                # Combinar chunks com seus scores
                chunks_with_scores: List[Tuple[Chunk, float]] = list(zip(chunks, scores))

                # Ordenar pela pontuação (decrescente)
                chunks_with_scores.sort(key=lambda item: item[1], reverse=True)

                span.set_attribute("reranker.output_chunks_count", len(chunks_with_scores))
                span.set_status(trace.StatusCode.OK)
                logger.info(f"Re-ranking concluído. {len(chunks_with_scores)} chunks reordenados com scores.")
                # Retornar a lista de tuplas (Chunk, score)
                return chunks_with_scores

            except Exception as e:
                 logger.error(f"Erro durante o re-ranking com CrossEncoder: {e}", exc_info=True)
                 span.record_exception(e)
                 span.set_status(trace.StatusCode.ERROR, description=str(e))
                 # Retornar lista original com scores 0.0 para manter o tipo de retorno
                 return [(chunk, 0.0) for chunk in chunks]
