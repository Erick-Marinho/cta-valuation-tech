import logging
import time # Para métricas de tempo
from typing import Dict, Any, Optional, List # Adicionar List

# Importar entidades do domínio
from domain.aggregates.document.document import Document
from domain.aggregates.document.chunk import Chunk

# Importar interfaces de repositórios (Domínio)
from domain.repositories.document_repository import DocumentRepository
from domain.repositories.chunk_repository import ChunkRepository

# Importar interfaces de serviços externos (Aplicação)
from application.interfaces.text_extractor import TextExtractor
from application.interfaces.chunker import Chunker, ChunkQualityEvaluator
from application.interfaces.embedding_provider import EmbeddingProvider

# Importar configurações (pode ser necessário para defaults)
from config.config import get_settings

# Exceção específica (pode ser definida em application/exceptions.py)
class DocumentProcessingError(Exception):
    pass

logger = logging.getLogger(__name__)

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
        chunk_evaluator: Optional[ChunkQualityEvaluator] = None,
    ):
        self._doc_repo = document_repository
        self._chunk_repo = chunk_repository
        self._extractor = text_extractor
        self._chunker = chunker
        self._embedder = embedding_provider
        self._evaluator = chunk_evaluator
        self._settings = get_settings()

    # Método auxiliar para determinar estratégia (pode ser movido para domínio/serviço se complexo)
    def _determine_chunk_strategy(self, file_name: str, metadata: Dict[str, Any]) -> str:
        # Lógica similar à do DocumentService original
        if file_name.lower().endswith((".md", ".markdown")):
            return "header_based"
        if metadata:
            if metadata.get("has_toc") or metadata.get("document_structure"):
                return "header_based"
            if metadata.get("tipo_documento") in ["artigo", "técnico", "manual", "guia"]:
                return "header_based"
        return "hybrid" # Ou outra estratégia padrão configurável

    async def execute(
        self,
        file_name: str,
        file_content: bytes,
        file_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_strategy: str = "auto",
    ) -> Document:
        """ Executa o processamento completo do documento. """
        start_time = time.time()
        logger.info(f"Iniciando processamento para documento: {file_name}")
        metadata = metadata or {}
        saved_doc: Optional[Document] = None # Para garantir que temos o ID

        try:
            # 1. Criar entidade Document inicial
            document = Document(
                name=file_name,
                file_type=file_type,
                content=file_content, # Manter conteúdo por enquanto para extração
                metadata=metadata,
            )

            # 2. Salvar Document inicial via _doc_repo.save() -> obter ID
            # É importante salvar cedo para ter um ID, mesmo que o resto falhe.
            try:
                 saved_doc = await self._doc_repo.save(document)
                 document.id = saved_doc.id
                 logger.info(f"Documento inicial salvo com ID: {document.id}")
            except Exception as e:
                 logger.exception(f"Falha crítica ao salvar registro inicial do documento {file_name}: {e}")
                 raise DocumentProcessingError(f"Não foi possível salvar o registro inicial do documento: {e}") from e

            # 3. Extrair texto via _extractor.extract()
            try:
                text, extracted_metadata, structure = await self._extractor.extract(document.content, document.file_type)
                logger.info(f"Texto extraído de {file_name}. Tamanho: {len(text)} caracteres.")
                # Limpar conteúdo binário da memória após extração
                document.content = bytes()
            except Exception as e:
                logger.exception(f"Falha ao extrair texto do documento {document.id}: {e}")
                raise DocumentProcessingError(f"Erro na extração de texto: {e}") from e

            # 4. Atualizar metadados do Document em memória com dados extraídos
            document.metadata.update({
                "extracted_metadata": extracted_metadata or {},
                "document_structure": structure or {},
            })

            # 5. (Opcional) Atualizar metadados no DB
            try:
                # Passar o objeto 'document' inteiro para save pode atualizar tudo
                await self._doc_repo.save(document)
                logger.debug(f"Metadados atualizados no DB para documento {document.id}")
            except Exception as e:
                # Logar, mas talvez não seja crítico parar aqui? Depende do requisito.
                logger.warning(f"Falha ao atualizar metadados no DB para doc {document.id} após extração: {e}")


            if not text or not text.strip():
                 logger.warning(f"Nenhum texto útil extraído do documento {document.id}. Processamento de chunks cancelado.")
                 document.processed = False # Marcar como não processado
                 document.chunks_count = 0
                 # Salvar o estado final (sem chunks)
                 await self._doc_repo.save(document)
                 return document

            # 6. Determinar estratégia de chunking
            effective_strategy = chunk_strategy
            if chunk_strategy == "auto":
                effective_strategy = self._determine_chunk_strategy(file_name, document.metadata)
            logger.info(f"Estratégia de chunking para {document.id}: {effective_strategy}")

            # 7. Dividir texto em chunks via _chunker.chunk()
            chunk_size = self._settings.CHUNK_SIZE
            chunk_overlap = self._settings.CHUNK_OVERLAP
            try:
                chunk_texts = await self._chunker.chunk(text, effective_strategy, chunk_size, chunk_overlap)
                logger.info(f"{len(chunk_texts)} chunks de texto gerados para documento {document.id}")
            except Exception as e:
                logger.exception(f"Falha no chunking do documento {document.id}: {e}")
                raise DocumentProcessingError(f"Erro no chunking: {e}") from e

            if not chunk_texts:
                logger.warning(f"Chunking não resultou em chunks para o documento {document.id}.")
                document.processed = False
                document.chunks_count = 0
                await self._doc_repo.save(document)
                return document

            # 8. Avaliar chunks via _evaluator.evaluate() (se disponível)
            quality_metrics = {}
            if self._evaluator:
                try:
                    quality_metrics = await self._evaluator.evaluate(chunk_texts, text)
                    logger.info(f"Qualidade dos chunks avaliada para doc {document.id}: {quality_metrics}")
                except Exception as e:
                    logger.warning(f"Falha ao avaliar qualidade dos chunks para doc {document.id}: {e}")
                    # Continuar mesmo se a avaliação falhar?

            # 9. Gerar embeddings via _embedder.embed_batch()
            try:
                embeddings = await self._embedder.embed_batch(chunk_texts)
                logger.info(f"{len(embeddings)} embeddings gerados para documento {document.id}")
                if len(embeddings) != len(chunk_texts):
                     raise DocumentProcessingError(f"Número de embeddings ({len(embeddings)}) não corresponde ao número de chunks ({len(chunk_texts)}).")
            except Exception as e:
                logger.exception(f"Falha ao gerar embeddings para documento {document.id}: {e}")
                raise DocumentProcessingError(f"Erro na geração de embeddings: {e}") from e

            # 10. Criar entidades Chunk
            chunks_to_save: List[Chunk] = []
            for i, (chunk_text, embedding) in enumerate(zip(chunk_texts, embeddings)):
                chunk_metadata = {
                    "chunk_index": i,
                    "total_chunks_generated": len(chunk_texts),
                    "chunking_strategy": effective_strategy,
                    # Adicionar métricas de qualidade se disponíveis
                    **{f"quality_{k}": v for k, v in quality_metrics.items()}
                }
                chunk_entity = Chunk(
                    document_id=document.id,
                    text=chunk_text,
                    embedding=embedding,
                    position=i,
                    metadata=chunk_metadata
                    # page_number - precisaria vir da extração/chunking
                )
                chunks_to_save.append(chunk_entity)

            # 11. Salvar chunks em lote via _chunk_repo.save_batch()
            try:
                # Assumindo que save_batch retorna os chunks salvos (com IDs)
                saved_chunks = await self._chunk_repo.save_batch(chunks_to_save)
                num_chunks_saved = len(saved_chunks) # Ou a implementação pode retornar a contagem
                logger.info(f"{num_chunks_saved} chunks salvos no DB para documento {document.id}")
            except Exception as e:
                logger.exception(f"Falha ao salvar chunks em lote para documento {document.id}: {e}")
                raise DocumentProcessingError(f"Erro ao salvar chunks: {e}") from e

            # 12. Atualizar entidade Document final
            document.chunks_count = num_chunks_saved
            document.processed = num_chunks_saved > 0

            # 13. Salvar estado final do Document no DB (com contagem de chunks)
            try:
                final_saved_doc = await self._doc_repo.save(document)
                logger.info(f"Estado final do documento {document.id} salvo (Processed: {final_saved_doc.processed}, Chunks: {final_saved_doc.chunks_count}).")
            except Exception as e:
                logger.warning(f"Falha ao salvar estado final do documento {document.id}: {e}")
                # Retornar o estado em memória mesmo assim? Ou relançar?
                # Por segurança, vamos retornar o estado que deveria ter sido salvo.

            # 14. Retornar entidade Document final
            end_time = time.time()
            logger.info(f"Documento {document.id} ({file_name}) processado com sucesso em {end_time - start_time:.2f}s.")
            return document # Retorna o estado final atualizado em memória

        except DocumentProcessingError as e:
             # Erro esperado durante o processamento
             logger.error(f"Erro de processamento para {file_name}: {e}")
             # Marcar documento como não processado ou com erro se já foi salvo
             if saved_doc and saved_doc.id:
                  try:
                       saved_doc.processed = False # Ou adicionar um status 'error'?
                       # Poderia adicionar detalhes do erro aos metadados
                       saved_doc.metadata["processing_error"] = str(e)
                       await self._doc_repo.save(saved_doc)
                  except Exception as db_err:
                       logger.error(f"Falha ao atualizar status de erro no DB para doc {saved_doc.id}: {db_err}")
             raise # Relança a exceção para a camada de interface tratar (ex: retornar erro HTTP)
        except Exception as e:
             # Erro inesperado
             logger.exception(f"Erro inesperado ao processar documento {file_name}: {e}")
             # Tentar atualizar status se possível
             if saved_doc and saved_doc.id:
                  try:
                       saved_doc.processed = False
                       saved_doc.metadata["processing_error"] = f"Unexpected error: {type(e).__name__}"
                       await self._doc_repo.save(saved_doc)
                  except Exception as db_err:
                       logger.error(f"Falha ao atualizar status de erro inesperado no DB para doc {saved_doc.id}: {db_err}")
             # Relança como erro de processamento genérico
             raise DocumentProcessingError(f"Erro inesperado no processamento: {e}") from e
