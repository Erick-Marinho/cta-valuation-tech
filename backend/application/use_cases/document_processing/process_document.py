import logging
import time # Para métricas de tempo
from typing import Dict, Any, Optional, List, Tuple # Adicionar Tuple
import re # <-- Adicionar import re
import hashlib # <-- Importar hashlib

# Importar entidades do domínio
from domain.aggregates.document.document import Document
from domain.aggregates.document.chunk import Chunk

# Importar interfaces de repositórios (Domínio)
from domain.repositories.document_repository import DocumentRepository
from domain.repositories.chunk_repository import ChunkRepository

# Importar interfaces de serviços externos (Aplicação)
from application.interfaces.text_extractor import TextExtractor
from application.interfaces.chunker import Chunker
from application.interfaces.embedding_provider import EmbeddingProvider

# Importar configurações (pode ser necessário para defaults)
from config.config import get_settings

# Exceção específica (pode ser definida em application/exceptions.py)
class DocumentProcessingError(Exception):
    pass

logger = logging.getLogger(__name__)

# --- Função Auxiliar de Limpeza (ou colocar em utils) ---
def clean_page_markers(text: str) -> str:
    """ Remove marcadores como [Página X] do início do texto. """
    # Regex para encontrar "[Página X]" (com ou sem espaço) no início da string,
    # possivelmente seguido por quebras de linha/espaços.
    pattern = r"^\[Página\s*\d+\]\s*"
    # pattern = r"\[Página\s*\d+\]" # Se quiser remover de qualquer lugar (menos seguro)
    return re.sub(pattern, "", text).strip()
# ------------------------------------------------------

class ProcessDocumentUseCase:
    """
    Caso de Uso para processar um novo documento: extrair texto,
    chunking, gerar embeddings e salvar tudo.
    """

    def __init__(
        self,
        document_repository: DocumentRepository,
        chunk_repository: ChunkRepository,
        text_extractor: TextExtractor,
        chunker: Chunker,
        embedding_provider: EmbeddingProvider,
    ):
        self._doc_repo = document_repository
        self._chunk_repo = chunk_repository
        self._extractor = text_extractor
        self._chunker = chunker
        self._embedder = embedding_provider
        self._settings = get_settings()

    async def execute(
        self,
        file_name: str,
        file_content: bytes,
        file_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Document:
        """ Executa o processamento completo do documento. """
        start_time = time.time()
        logger.info(f"Iniciando processamento para documento: {file_name}")
        initial_metadata = metadata or {}
        saved_doc: Optional[Document] = None
        document_id: Optional[int] = None
        original_size_kb = len(file_content) / 1024 if file_content else 0.0
        content_hash = hashlib.sha256(file_content).hexdigest() if file_content else None
        enriched_metadata = initial_metadata.copy()
        enriched_metadata["content_hash_sha256"] = content_hash

        # --- CORREÇÃO DA ESTRUTURA try/except ---
        try: # <-- Bloco TRY principal engloba todo o processamento
            # --- Extração de Metadados ---
            try: # <-- Try interno para extração de metadados
                doc_extracted_metadata = await self._extractor.extract_document_metadata(file_content, file_type)
                for key, value in doc_extracted_metadata.items():
                     if key not in enriched_metadata:
                          enriched_metadata[key] = value
            except Exception as meta_err:
                 logger.warning(f"Falha ao extrair metadados do documento {file_name}: {meta_err}")
                 enriched_metadata["metadata_extraction_status"] = "failed"
            # ------------------------------------

            # 1. Criar entidade Document inicial
            document = Document(
                name=file_name,
                file_type=file_type,
                metadata=enriched_metadata,
                size_kb=original_size_kb,
            )

            # 2. Salvar Document inicial
            try: # <-- Try interno para salvar doc inicial
                 saved_doc = await self._doc_repo.save(document)
                 if not saved_doc or not saved_doc.id:
                      raise DocumentProcessingError(f"Repositório não retornou um ID válido ao salvar doc inicial para {file_name}")
                 document_id = saved_doc.id
                 document.id = document_id # Atualizar objeto em memória com ID
                 logger.info(f"Documento inicial salvo com ID: {document_id}")
            except Exception as e: # Captura erro do save inicial
                 logger.exception(f"Falha crítica ao salvar registro inicial do documento {file_name}: {e}")
                 # Relança como DocumentProcessingError para ser pego pelo except principal
                 raise DocumentProcessingError(f"Não foi possível salvar o registro inicial do documento: {e}") from e

            # 3. Extrair texto por página
            pages_data: List[Dict[str, Any]] = []
            try: # <-- Try interno para extração de texto
                pages_data = await self._extractor.extract_text(file_content, file_type)
                if not pages_data:
                    logger.warning(f"Nenhum texto/página extraído do documento {file_name} (ID: {document_id}). Marcando como falha.")
                    raise DocumentProcessingError(f"Falha na extração de texto (sem páginas) para {file_name}")
                logger.info(f"Texto extraído de {len(pages_data)} páginas para doc ID {document_id}.")
            except NotImplementedError as nie: # Captura erro específico do extrator
                 logger.error(f"Tipo de arquivo '{file_type}' não suportado pelo extrator para {file_name} (ID: {document_id}).")
                 raise DocumentProcessingError(f"Tipo de arquivo não suportado: {file_type}") from nie
            except Exception as e: # Captura outros erros de extração
                logger.exception(f"Falha ao extrair texto do documento {document_id}: {e}")
                raise DocumentProcessingError(f"Erro na extração de texto: {e}") from e

            # ----- INÍCIO DO LOOP DE PROCESSAMENTO DE PÁGINAS E CHUNKS -----
            chunks_to_save: List[Tuple[Chunk, List[float]]] = []
            total_chunks_attempted = 0 # Renomeado para clareza

            for page_data in pages_data:
                page_num = page_data.get("page_number")
                page_text_raw = page_data.get("text", "")
                if not page_num:
                    logger.warning(f"Dados inválidos para página (Num: {page_num}) em doc ID {document_id}. Pulando.")
                    continue
                page_text_cleaned = clean_page_markers(page_text_raw)
                if not page_text_cleaned and page_text_raw:
                    logger.warning(f"Texto da página {page_num} (Doc ID: {document_id}) ficou vazio após limpeza.")
                logger.debug(f"[DEBUG] Processando Página: {page_num} (Doc ID: {document_id})")

                page_chunks_data: List[Dict[str, Any]] = []
                try:
                    chunk_base_metadata = {}
                    page_chunks_data = await self._chunker.split_page_to_chunks(
                        page_number=page_num,
                        page_text=page_text_cleaned,
                        base_metadata=chunk_base_metadata
                    )
                except Exception as chunk_err:
                    logger.error(f"Erro durante o chunking da página {page_num} (Doc ID: {document_id}): {chunk_err}", exc_info=True)
                    continue # Pula para a próxima página

                logger.debug(f"[DEBUG] Chunker retornou {len(page_chunks_data)} chunks para a página {page_num} (Doc ID: {document_id}).")

                # Gerar embeddings para os chunks da página atual
                page_chunk_embeddings: List[List[float]] = []
                chunk_texts_for_embedding: List[str] = [d.get("text", "") for d in page_chunks_data if d.get("text")]

                if chunk_texts_for_embedding:
                    try:
                        page_chunk_embeddings = await self._embedder.embed_batch(chunk_texts_for_embedding)
                        if len(page_chunk_embeddings) != len(chunk_texts_for_embedding):
                             logger.error(f"Número de embeddings ({len(page_chunk_embeddings)}) diferente do número de textos ({len(chunk_texts_for_embedding)}) para página {page_num}. Pulando página.")
                             continue # Pula página se houver erro crítico no batch
                    except Exception as embed_err:
                        logger.error(f"Erro ao gerar embeddings para chunks da página {page_num} (Doc ID: {document_id}): {embed_err}", exc_info=True)
                        continue # Pula para a próxima página

                # Criar entidades Chunk (sem embedding) e preparar tuplas para salvar
                embedding_idx = 0
                for i, chunk_data in enumerate(page_chunks_data):
                    chunk_text = chunk_data.get("text", "")
                    chunk_metadata = chunk_data.get("metadata", {})
                    if "page_number" not in chunk_metadata:
                        chunk_metadata["page_number"] = page_num
                    chunk_page_num = chunk_metadata.get("page_number")

                    if not chunk_text: continue # Pula chunk vazio

                    # Tenta obter o embedding correspondente
                    current_embedding = []
                    if embedding_idx < len(page_chunk_embeddings):
                        current_embedding = page_chunk_embeddings[embedding_idx]; embedding_idx += 1
                    else:
                        # Isso não deveria acontecer se a verificação anterior passou, mas por segurança:
                        logger.error(f"Faltando embedding inesperadamente para chunk {i}, pág {chunk_page_num}, doc {document_id}. Pulando chunk.")
                        continue

                    total_chunks_attempted += 1 # Incrementa contador de chunks tentados

                    # Criar entidade Chunk SEM o embedding
                    domain_chunk = Chunk(
                        document_id=document_id,
                        text=chunk_text,
                        page_number=chunk_page_num,
                        position=total_chunks_attempted - 1, # Usar contador como posição global (ou ajustar se necessário)
                        metadata=chunk_metadata
                    )
                    # Adicionar tupla (Chunk, embedding) à lista para salvar
                    chunks_to_save.append((domain_chunk, current_embedding))

            # ----- FIM DO LOOP -----

            logger.info(f"Total de {len(chunks_to_save)} chunks preparados para salvar para doc ID {document_id}.")

            # 6. Salvar chunks em lote (DENTRO do try principal)
            num_chunks_saved = 0
            if chunks_to_save: # <-- Usar a nova lista de tuplas
                try:
                    # Chamar save_batch com a lista de tuplas
                    saved_domain_chunks: List[Chunk] = await self._chunk_repo.save_batch(chunks_to_save)

                    # A contagem de sucesso é o número de chunks retornados pelo save_batch
                    num_chunks_saved = len(saved_domain_chunks)
                    logger.info(f"{num_chunks_saved} chunks salvos no DB para documento {document_id}")
                except Exception as e:
                    logger.exception(f"Falha ao salvar chunks em lote para documento {document_id}: {e}")
                    raise DocumentProcessingError(f"Erro ao salvar chunks: {e}") from e
            else:
                logger.warning(f"Nenhum chunk foi gerado/preparado para salvar para doc ID {document_id}.")

            # 7. Atualizar entidade Document final (usar num_chunks_saved)
            document.chunks_count = num_chunks_saved # <-- Usar a contagem retornada
            document.processed = num_chunks_saved > 0
            document.metadata["page_count"] = len(pages_data) # Mantém contagem de páginas
            document.size_kb = original_size_kb
            document.metadata["processing_status"] = "success"
            document.metadata.pop("processing_error", None)
            document.metadata.pop("metadata_extraction_status", None)

            # 8. Salvar estado final do Document no DB (DENTRO do try principal)
            document_to_return: Document
            try: # Try interno para salvar estado final
                final_saved_doc = await self._doc_repo.save(document)
                logger.info(f"Estado final do documento {document.id} salvo (Processed: {final_saved_doc.processed}, Chunks: {final_saved_doc.chunks_count}, SizeKB: {final_saved_doc.size_kb:.2f}).")
                document_to_return = final_saved_doc
            except Exception as e: # Captura erro do save final
                logger.warning(f"Falha ao salvar estado final do documento {document.id}: {e}")
                document_to_return = document # Retorna o estado em memória como fallback

            # 9. Retornar entidade Document final (DENTRO do try principal)
            end_time = time.time()
            logger.info(f"Documento {document.id} ({file_name}) processado com sucesso em {end_time - start_time:.2f}s.")
            return document_to_return

        # --- Bloco EXCEPT principal (NÍVEL 1) ---
        except DocumentProcessingError as e: # Captura erros de processamento esperados
             logger.error(f"Erro de processamento para {file_name} (Doc ID: {document_id}): {e}")
             doc_id_to_update = document_id or (saved_doc.id if saved_doc else None)
             if doc_id_to_update:
                  try:
                       # Tentar marcar o doc como falho no DB
                       doc_to_update = await self._doc_repo.find_by_id(doc_id_to_update)
                       if doc_to_update:
                            doc_to_update.processed = False
                            doc_to_update.metadata.update({
                                "processing_status": "failed",
                                "processing_error": str(e)
                            })
                            await self._doc_repo.save(doc_to_update)
                            logger.info(f"Status de erro atualizado para doc ID {doc_id_to_update}")
                       else:
                            logger.warning(f"Não foi possível encontrar doc {doc_id_to_update} para atualizar status de erro.")
                  except Exception as db_err:
                       logger.error(f"Falha ao atualizar status de erro no DB para doc {doc_id_to_update}: {db_err}")
             raise # Relança a DocumentProcessingError original

        except Exception as e: # Captura qualquer outro erro inesperado
             logger.exception(f"Erro inesperado ao processar documento {file_name} (Doc ID: {document_id}): {e}")
             doc_id_to_update = document_id or (saved_doc.id if saved_doc else None)
             if doc_id_to_update:
                  try:
                       # Tentar marcar o doc como falho no DB
                       doc_to_update = await self._doc_repo.find_by_id(doc_id_to_update)
                       if doc_to_update:
                            doc_to_update.processed = False
                            doc_to_update.metadata.update({
                                "processing_status": "failed",
                                "processing_error": f"Unexpected error: {type(e).__name__}"
                            })
                            await self._doc_repo.save(doc_to_update)
                            logger.info(f"Status de erro inesperado atualizado para doc ID {doc_id_to_update}")
                       else:
                           logger.warning(f"Não foi possível encontrar doc {doc_id_to_update} para atualizar status de erro inesperado.")
                  except Exception as db_err:
                       logger.error(f"Falha ao atualizar status de erro inesperado no DB para doc {doc_id_to_update}: {db_err}")
             # Encapsula o erro inesperado em DocumentProcessingError antes de relançar
             raise DocumentProcessingError(f"Erro inesperado no processamento: {e}") from e
        # --- FIM DA CORREÇÃO ---
