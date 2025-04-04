import logging
from typing import List
from sentence_transformers import SentenceTransformer
from backend.core.models.chunk import Chunk
from .base import Embedder

# Configuração básica de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SentenceTransformerEmbedder(Embedder):
    """Implementação de Embedder usando a biblioteca sentence-transformers."""

    def __init__(self, model_name: str = "paraphrase-multilingual-mpnet-base-v2", batch_size: int = 32, device: str = "cpu"):
        """
        Inicializa o SentenceTransformerEmbedder.

        Args:
            model_name: O nome do modelo sentence-transformer a ser usado.
            batch_size: O tamanho do lote para processamento de embeddings.
            device: O dispositivo para carregar o modelo ('cpu', 'cuda').
        """
        logger.info(f"Carregando modelo SentenceTransformer: {model_name} em {device}")
        try:
            self.model = SentenceTransformer(model_name, device=device)
            self.batch_size = batch_size
            logger.info(f"Modelo {model_name} carregado com sucesso.")
        except Exception as e:
            logger.error(f"Falha ao carregar o modelo SentenceTransformer {model_name}: {e}", exc_info=True)
            raise

    def embed(self, chunks: List[Chunk]) -> List[Chunk]:
        """Gera embeddings para os chunks usando sentence-transformers."""
        if not chunks:
            logger.info("Nenhum chunk recebido para gerar embeddings.")
            return []

        texts = [chunk.text for chunk in chunks if chunk.text] # Extrai textos não vazios
        if not texts:
            logger.warning("Todos os chunks recebidos tinham texto vazio.")
            return chunks # Retorna os chunks originais se todos forem vazios

        logger.info(f"Gerando embeddings para {len(texts)} textos com batch_size={self.batch_size}...")

        try:
            embeddings = self.model.encode(
                texts,
                batch_size=self.batch_size,
                show_progress_bar=True # Útil para logs/debug
            )
            logger.info(f"Embeddings gerados com sucesso. Dimensão: {embeddings.shape}")

            # Associa os embeddings de volta aos Chunks originais
            # É crucial manter a ordem e lidar com chunks que tinham texto vazio
            embedding_iter = iter(embeddings)
            for chunk in chunks:
                if chunk.text:
                    chunk.embedding = next(embedding_iter).tolist() # Converte numpy array para list[float]
                else:
                    # Decide como lidar com chunks vazios: deixar embedding vazio ou usar um vetor zero?
                    # Por enquanto, deixaremos vazio (default_factory=list fará isso)
                    pass # chunk.embedding já é [] por padrão

            return chunks

        except Exception as e:
            logger.error(f"Erro durante a geração de embeddings: {e}", exc_info=True)
            # Decide como tratar o erro: retornar chunks parcialmente processados,
            # lançar exceção, etc. Lançar é mais seguro para indicar falha.
            raise RuntimeError(f"Falha ao gerar embeddings com {self.model.config.name}") from e

    async def aembed(self, chunks: List[Chunk]) -> List[Chunk]:
        """
        Versão assíncrona de 'embed'.
        NOTA: sentence_transformers.encode não é nativamente async.
        Para I/O bound tasks (como chamar uma API externa), async é crucial.
        Para CPU-bound tasks como rodar um modelo localmente, rodar em um
        executor separado (como thread pool) pode ser mais apropriado
        se chamado de um contexto async. Por simplicidade, vamos chamar
        a versão síncrona aqui, mas em produção, considere `run_in_executor`.
        """
        # Import necessário apenas se for usar run_in_executor
        # import asyncio
        # loop = asyncio.get_running_loop()
        # return await loop.run_in_executor(None, self.embed, chunks) # Executa self.embed em um thread pool

        # Implementação síncrona simples por enquanto
        logger.warning("Executando 'aembed' de forma síncrona. Considere `run_in_executor` para produção.")
        return self.embed(chunks)
