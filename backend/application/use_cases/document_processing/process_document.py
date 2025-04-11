import logging
import time # Para métricas de tempo
from typing import Dict, Any, Optional, List, Tuple # Adicionar Tuple
import re # <-- Adicionar import re
import hashlib # <-- Importar hashlib

# Importar entidades do domínio
from domain.aggregates.document.document import Document
from domain.aggregates.document.chunk import Chunk
from domain.value_objects.embedding import Embedding # Certifique-se que este import existe ou adicione
from domain.aggregates.document.document_metadata import DocumentMetadata # <-- Adicionar import do VO Metadata

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
        if not hasattr(self._chunk_repo, "save_batch_with_embeddings"):
            raise TypeError(f"A implementação de ChunkRepository ({type(self._chunk_repo).__name__}) não suporta 'save_batch_with_embeddings'.")

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
        initial_metadata_dict = metadata or {} # Renomear para clareza
        enriched_metadata_dict = initial_metadata_dict.copy() # Trabalhar com um dicionário temporário
        enriched_metadata_dict["content_hash_sha256"] = hashlib.sha256(file_content).hexdigest() if file_content else None
        enriched_metadata_dict["source_filename"] = file_name # Adicionar nome original ao dict

        # --- Extração de Metadados (já existente) ---
        try:
            doc_extracted_metadata = await self._extractor.extract_document_metadata(file_content, file_type)
            # Atualizar o dicionário temporário com metadados extraídos
            for key, value in doc_extracted_metadata.items():
                 # Evitar sobrescrever chaves já existentes como content_hash? Ou permitir? Decidir política.
                 # if key not in enriched_metadata_dict:
                 enriched_metadata_dict[key] = value
            enriched_metadata_dict["extraction_status"] = "success" # Atualizar status no dict
        except Exception as meta_err:
             logger.warning(f"Falha ao extrair metadados do documento {file_name}: {meta_err}")
             enriched_metadata_dict["extraction_status"] = "failed" # Atualizar status no dict
        # ------------------------------------

        # 1. Criar entidade Document inicial, passando o dicionário para o DocumentMetadata
        document = Document(
            name=file_name,
            file_type=file_type,
            # Criar o VO DocumentMetadata a partir do dicionário enriquecido
            metadata=DocumentMetadata.from_dict(enriched_metadata_dict), # <-- MUDANÇA: Usar from_dict
            size_kb=len(file_content) / 1024 if file_content else 0.0,
            # processed e chunks_count são definidos depois
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
        total_chunks_attempted = 0
        total_chunks_failed = 0

        for page_num, page_content in enumerate(pages_data, 1):
            page_text = page_content.get("text", "")
            if not page_text.strip():
                continue
            page_text_cleaned = clean_page_markers(page_text)
            if not page_text_cleaned and page_text:
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

            # Preparar textos para embedding
            chunk_texts_for_embedding: List[str] = [chunk_data.get("text", "") for chunk_data in page_chunks_data if chunk_data.get("text")]
            chunk_metadata_list: List[Dict[str, Any]] = [chunk_data.get("metadata", {}) for chunk_data in page_chunks_data if chunk_data.get("text")] # Para metadados originais do chunker

            page_chunk_embeddings_vectors: List[List[float]] = []
            if chunk_texts_for_embedding:
                try:
                    # Geração de embeddings (retorna List[Embedding])
                    page_chunk_embedding_objects: List[Embedding] = await self._embedder.embed_batch(chunk_texts_for_embedding)
                    # Extrair vetores
                    page_chunk_embeddings_vectors = [emb.vector for emb in page_chunk_embedding_objects]
                    # Validar tamanho (já existente)
                    if len(page_chunk_embeddings_vectors) != len(chunk_texts_for_embedding):
                        logger.error(f"Número de embeddings ({len(page_chunk_embedding_objects)}) diferente do número de textos ({len(chunk_texts_for_embedding)}) para página {page_num}. Pulando página.")
                        total_chunks_failed += len(chunk_texts_for_embedding) # Contar como falha
                        continue # Pular página

                except Exception as embed_err:
                    logger.error(f"Erro ao gerar embeddings para chunks da página {page_num} (Doc ID: {document_id}): {embed_err}", exc_info=True)
                    total_chunks_failed += len(chunk_texts_for_embedding) # Contar como falha
                    continue # Pular página

            # Criar entidades Chunk e preparar lista de tuplas para salvar
            embedding_idx = 0
            for i, chunk_data in enumerate(page_chunks_data):
                 chunk_text = chunk_data.get("text", "")
                 chunk_metadata = chunk_data.get("metadata", {}) # Metadados vindos do chunker
                 if not chunk_text: continue

                 if embedding_idx < len(page_chunk_embeddings_vectors):
                     current_embedding_vector = page_chunk_embeddings_vectors[embedding_idx]

                     # Criar a entidade Chunk (ainda sem ID)
                     domain_chunk = Chunk(
                         document_id=document_id,
                         text=chunk_text,
                         page_number=chunk_metadata.get("page_number", page_num), # Usar page_num se não vier do metadata
                         position=total_chunks_attempted, # Posição global (ajustar se necessário)
                         metadata=chunk_metadata # Usar metadados do chunker
                     )
                     # Adicionar tupla (Chunk, embedding_vector) à lista
                     chunks_to_save.append((domain_chunk, current_embedding_vector)) # <-- Montar tupla aqui
                     total_chunks_attempted += 1
                     embedding_idx += 1
                 else:
                     logger.error(f"Faltando embedding para chunk {i}, pág {page_num}, doc {document_id}.")
                     total_chunks_failed += 1 # Contar como falha

        # ----- FIM DO LOOP -----

        logger.info(f"Total de {len(chunks_to_save)} chunks preparados para salvar para doc ID {document_id}.")

        # 6. Salvar chunks e embeddings em lote
        saved_chunks: List[Chunk] = []
        if chunks_to_save:
            logger.info(f"Preparando para salvar {len(chunks_to_save)} chunks com embeddings para doc ID {document_id}.")
            try:
                 # Chamar o método específico da implementação
                 # Não precisamos mais da verificação de tipo aqui por causa do check no __init__
                 saved_chunks = await self._chunk_repo.save_batch_with_embeddings(chunks_to_save) # <-- CHAMADA AO NOVO MÉTODO

                 if len(saved_chunks) != len(chunks_to_save):
                     logger.warning(f"Número de chunks salvos ({len(saved_chunks)}) difere do número enviado ({len(chunks_to_save)}).")
                     # Pode indicar falhas parciais no salvamento em lote

                 logger.info(f"{len(saved_chunks)} chunks efetivamente salvos para o documento {document_id}.")

            except NotImplementedError:
                 # Caso o check no __init__ falhe ou seja removido
                 logger.error(f"A implementação do ChunkRepository ({type(self._chunk_repo).__name__}) não suporta save_batch_with_embeddings.")
                 raise DocumentProcessingError("Erro interno: Repositório de Chunks incompatível.") from None
            except Exception as e:
                logger.exception(f"Erro ao salvar chunks em lote para documento {document_id}: {e}")
                # Considerar se deve levantar erro ou tentar salvar o estado parcial do documento
                raise DocumentProcessingError(f"Falha ao salvar chunks: {e}") from e

        # 7. Atualizar estado final do Documento
        # Se precisarmos atualizar metadados finais aqui:
        final_metadata_updates = {
            "processing_status": "completed", # Exemplo de metadado final
            # Poderia adicionar estatísticas de chunks aqui se quisesse
            # "chunks_attempted": total_chunks_attempted,
            # "chunks_failed": total_chunks_failed
        }
        # Usar um método helper em Document ou recriar o metadata VO
        current_meta_dict = document.metadata.to_dict()
        current_meta_dict.update(final_metadata_updates)
        document.metadata = DocumentMetadata.from_dict(current_meta_dict) # <-- MUDANÇA: Atualizar metadata via VO

        document.processed = True
        document.chunks_count = len(saved_chunks)
        logger.info(f"Documento {document_id} processado. Chunks salvos: {document.chunks_count}. Status metadados: {document.metadata.extraction_status}") # Acessar campo do VO

        # 8. Salvar estado final do Document no DB (DENTRO do try principal)
        document_to_return: Document
        try: # Try interno para salvar estado final
            final_saved_doc = await self._doc_repo.save(document)
            logger.info(f"Estado final do documento {document.id} salvo.")
            document_to_return = final_saved_doc
        except Exception as e: # Captura erro do save final
            logger.warning(f"Falha ao salvar estado final do documento {document.id}: {e}")
            document_to_return = document # Retorna o estado em memória como fallback

        # 9. Retornar entidade Document final (DENTRO do try principal)
        end_time = time.time()
        logger.info(f"Documento {document.id} ({file_name}) processado com sucesso em {end_time - start_time:.2f}s.")
        return document_to_return
