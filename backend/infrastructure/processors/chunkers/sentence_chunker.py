import asyncio
import logging
from typing import List, Dict, Any, Optional
import nltk # Importar NLTK

# Importar Interface da Aplicação
from application.interfaces.chunker import Chunker
# Importar Configurações
from config.config import get_settings

logger = logging.getLogger(__name__)

# --- Download de Dados NLTK (Necessário apenas uma vez) ---
try:
    nltk.data.find('tokenizers/punkt')
    logger.debug("NLTK 'punkt' tokenizer já está disponível.")
except LookupError:
    logger.info("Baixando NLTK 'punkt' tokenizer...")
    try:
        nltk.download('punkt', quiet=True)
        logger.info("NLTK 'punkt' baixado com sucesso.")
    except Exception as e:
        logger.error(f"Falha ao baixar NLTK 'punkt'. O chunking por sentença pode falhar: {e}", exc_info=True)
        # Considerar levantar um erro aqui se for crítico para a aplicação iniciar
# ------------------------------------------------------------

class SentenceChunker(Chunker):
    """
    Implementação de Chunker que divide o texto em sentenças e as agrupa
    em chunks de tamanho definido, com sobreposição baseada em sentenças.
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        overlap_sentences: int = 1, # Define overlap por número de sentenças
    ):
        """
        Inicializa o SentenceChunker.

        Args:
            chunk_size: Tamanho máximo alvo para cada chunk (em caracteres).
                        Se None, usa o valor de settings.CHUNK_SIZE.
            overlap_sentences: Número de sentenças do final do chunk anterior
                               a serem repetidas no início do próximo chunk.
        """
        self.settings = get_settings()
        self.chunk_size = chunk_size or self.settings.CHUNK_SIZE
        # Garantir que o overlap seja pelo menos 0
        self.overlap_sentences = max(0, overlap_sentences)
        # Delimitador para juntar sentenças (parágrafo preserva mais contexto)
        self.sentence_joiner = "\n" # Ou " " se preferir mais compacto

        logger.info(
            f"SentenceChunker inicializado com chunk_size={self.chunk_size}, "
            f"overlap_sentences={self.overlap_sentences}"
        )

    async def split_page_to_chunks(
        self,
        page_number: int,
        page_text: str,
        base_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """ Divide o texto da página baseado em sentenças. """
        if not page_text or not page_text.strip():
            logger.debug(f"Texto vazio ou apenas espaços em branco para página {page_number}. Nenhum chunk gerado.")
            return []

        try:
            # Usar asyncio.to_thread para a tokenização que pode ser CPU-bound
            def sync_tokenize():
                try:
                     return nltk.sent_tokenize(page_text, language='portuguese') # Especificar idioma ajuda
                except Exception as tokenize_err:
                     logger.error(f"Erro ao tokenizar sentenças na página {page_number}: {tokenize_err}", exc_info=True)
                     # Fallback: tratar a página inteira como uma única "sentença"
                     return [page_text.strip()]

            sentences: List[str] = await asyncio.to_thread(sync_tokenize)

        except Exception as e:
             logger.error(f"Erro inesperado durante a tokenização NLTK na página {page_number}: {e}", exc_info=True)
             return [] # Retornar vazio se a tokenização falhar

        if not sentences:
            logger.debug(f"Nenhuma sentença encontrada após tokenização na página {page_number}.")
            return []

        page_metadata = base_metadata or {}
        page_metadata["page_number"] = page_number

        chunk_list: List[Dict[str, Any]] = []
        current_chunk_sentences: List[str] = []
        current_chunk_len = 0
        len_joiner = len(self.sentence_joiner)

        for i, sentence in enumerate(sentences):
            sentence_len = len(sentence)
            # Calcular tamanho potencial se adicionar a sentença atual
            potential_len = current_chunk_len + sentence_len + (len_joiner if current_chunk_sentences else 0)

            # Se cabe ou é a primeira sentença do chunk
            if potential_len <= self.chunk_size or not current_chunk_sentences:
                current_chunk_sentences.append(sentence)
                current_chunk_len = potential_len
            else:
                # Finalizar o chunk atual
                chunk_text = self.sentence_joiner.join(current_chunk_sentences)
                chunk_list.append({"text": chunk_text, "metadata": page_metadata.copy()}) # Usar cópia dos metadados

                # Preparar o próximo chunk com overlap
                # Pegar as últimas 'overlap_sentences' do chunk que acabamos de formar
                overlap_part = current_chunk_sentences[-self.overlap_sentences:] if self.overlap_sentences > 0 else []

                # Começar novo chunk com overlap + sentença atual
                current_chunk_sentences = overlap_part + [sentence]
                # Recalcular tamanho do novo chunk inicial
                current_chunk_len = len(self.sentence_joiner.join(current_chunk_sentences))


        # Adicionar o último chunk se houver sentenças restantes
        if current_chunk_sentences:
            chunk_text = self.sentence_joiner.join(current_chunk_sentences)
            # Garantir que mesmo o último chunk não exceda (pode acontecer se uma única sentença for muito grande)
            if len(chunk_text) > self.chunk_size:
                 logger.warning(f"Último chunk da página {page_number} excedeu chunk_size ({len(chunk_text)} > {self.chunk_size}). Pode indicar sentença muito longa.")
                 # Opção 1: Truncar (simples)
                 # chunk_text = chunk_text[:self.chunk_size]
                 # Opção 2: Dividir a última sentença (complexo, pode usar RecursiveCharacterTextSplitter como fallback aqui)
                 # Por simplicidade, vamos permitir que exceda por enquanto, mas logamos.
            chunk_list.append({"text": chunk_text, "metadata": page_metadata.copy()})

        logger.info(f"Página {page_number} dividida em {len(chunk_list)} chunks usando SentenceChunker.")
        return chunk_list
