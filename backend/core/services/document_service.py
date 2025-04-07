"""
Serviço para gerenciamento e processamento de documentos.
"""

import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from core.config import get_settings
from core.exceptions import DocumentProcessingError
from ..models.document import Document
from .embedding_service import get_embedding_service
from processors.extractors.pdf_extractor import PDFExtractor
from processors.chunkers.semantic_chunker import (
    create_semantic_chunks,
    evaluate_chunk_quality,
)
from db.repositories.document_repository import DocumentoRepository
from db.repositories.chunk_repository import ChunkRepository
from utils.logging import track_timing
from utils.metrics_prometheus import (
    record_document_processing,
    record_chunk_size,
    record_extraction_time,
    record_chunking_quality,
)
from utils.telemetry import get_tracer
from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode
from opentelemetry.semconv.trace import SpanAttributes

logger = logging.getLogger(__name__)


class DocumentService:
    """
    Serviço para operações com documentos.

    Responsabilidades:
    - Processamento de documentos
    - Extração de texto
    - Chunking
    - Geração de embeddings
    - Armazenamento no banco de dados
    """

    def __init__(self):
        """
        Inicializa o serviço de documentos.
        """
        self.tracer = get_tracer(__name__)
        with self.tracer.start_as_current_span(
            "document_service.__init__", kind=SpanKind.INTERNAL
        ) as span:
            self.settings = get_settings()
            self.embedding_service = get_embedding_service()
            span.set_attribute("dependencies_initialized", ["EmbeddingService"])
            span.set_status(Status(StatusCode.OK))

    def _determine_document_type(self, file_name: str, metadata: Dict[str, Any]) -> str:
        """
        Determina o tipo de documento para escolher a melhor estratégia de chunking.

        Args:
            file_name: Nome do arquivo
            metadata: Metadados do documento

        Returns:
            str: Estratégia recomendada para chunking
        """
        # Determinar por extensão do arquivo
        if file_name.lower().endswith((".md", ".markdown")):
            return "header_based"  # Markdown geralmente tem estrutura de cabeçalhos

        # Determinar por metadados, se disponíveis
        if metadata:
            # Se tiver informação sobre estrutura do documento
            if metadata.get("has_toc") or metadata.get("document_structure"):
                return "header_based"

            # Se for um artigo científico ou técnico
            if metadata.get("tipo_documento") in [
                "artigo",
                "técnico",
                "manual",
                "guia",
            ]:
                return "header_based"

        # Padrão para PDFs
        return "hybrid"  # Estratégia mais versátil como padrão

    @track_timing
    async def process_document(
        self,
        file_name: str,
        file_content: bytes,
        file_type: str = "pdf",
        metadata: Dict[str, Any] = None,
        chunk_strategy: str = "auto",
    ) -> Document:
        """
        Processa um documento completo: extrai texto, divide em chunks e gera embeddings.

        Args:
            file_name: Nome do arquivo
            file_content: Conteúdo binário do arquivo
            file_type: Tipo do arquivo (por padrão, pdf)
            metadata: Metadados adicionais do documento
            chunking_strategy: Estratégia de chunking ("auto", "header_based", "paragraph", "hybrid")

        Returns:
            Document: Documento processado
        """

        processing_start = time.time()
        suggested_strategy = chunk_strategy  # Usar a variável da assinatura

        with self.tracer.start_as_current_span(
            "document_service.process_document",
            kind=SpanKind.SERVER,  # Representa o processamento de uma "requisição" de documento
        ) as span:
            span.set_attribute("document.name", file_name)
            span.set_attribute("document.type", file_type)
            span.set_attribute("document.size_bytes", len(file_content))
            span.set_attribute(
                "document.initial_metadata_keys",
                str(list(metadata.keys()) if metadata else []),
            )
            span.set_attribute("document.chunk_strategy_input", chunk_strategy)

            db_document_id = None  # Inicializar ID

            try:
                # 1. Criar instância de documento
                document = Document(
                    name=file_name,
                    file_type=file_type,
                    content=file_content,
                    metadata=metadata or {},
                )

                # 2. Salvar documento no banco de dados
                with self.tracer.start_as_current_span(
                    "db.save_initial_document", kind=SpanKind.CLIENT
                ) as db_save_span:
                    db_save_span.set_attribute(SpanAttributes.DB_SYSTEM, "postgresql")
                    db_save_span.set_attribute(SpanAttributes.DB_OPERATION, "INSERT")
                    db_save_span.set_attribute(
                        SpanAttributes.DB_SQL_TABLE, "documentos_originais"
                    )
                    db_save_span.set_attribute(
                        "document.name", document.name
                    )  # Repetir aqui para contexto do DB
                    try:
                        db_document_id = DocumentoRepository.criar_documento(
                            nome_arquivo=document.name,
                            tipo_arquivo=document.file_type,
                            conteudo_binario=document.content,  # Passar conteúdo aqui
                            metadados=document.metadata,
                        )
                        if db_document_id:
                            db_save_span.set_attribute("db.document_id", db_document_id)
                            db_save_span.set_status(Status(StatusCode.OK))
                        else:
                            db_save_span.set_status(
                                Status(
                                    StatusCode.ERROR,
                                    "Falha ao obter ID do documento após salvar.",
                                )
                            )
                            # Métrica Prometheus (manter)
                            record_document_processing("error_db_save", file_type)
                            raise DocumentProcessingError(
                                f"Erro ao salvar documento {file_name} no DB (sem ID retornado)"
                            )
                    except Exception as e:
                        db_save_span.record_exception(e)
                        db_save_span.set_status(Status(StatusCode.ERROR, str(e)))
                        record_document_processing(
                            "error_db_save", file_type
                        )  # Métrica
                        raise  # Relançar para ser pego pelo try/except principal

                document.id = db_document_id
                span.set_attribute(
                    "db.document_id", db_document_id
                )  # Adicionar ID ao span principal

                # 3. Extrair texto conforme o tipo de arquivo
                extraction_start = time.time()
                with self.tracer.start_as_current_span(
                    "document.extract_text", kind=SpanKind.INTERNAL
                ) as extraction_actual_span:
                    extraction_actual_span.set_attribute(
                        "document.type", document.file_type
                    )
                    try:
                        if document.is_pdf:
                            # Extrair texto e metadados do PDF
                            text, pdf_metadata, structure = PDFExtractor.extract_all(
                                file_content
                            )
                            extraction_actual_span.set_attribute(
                                "extraction.tool", "PDFExtractor"
                            )
                            extraction_actual_span.set_attribute(
                                "extraction.text_length", len(text)
                            )
                            extraction_actual_span.set_attribute(
                                "extraction.metadata_found", bool(pdf_metadata)
                            )
                            extraction_actual_span.set_attribute(
                                "extraction.structure_found", bool(structure)
                            )
                            extraction_actual_span.set_status(Status(StatusCode.OK))

                            # Atualizar metadados com informações do PDF
                            document.metadata.update(
                                {
                                    "pdf_metadata": pdf_metadata or {},  # Garantir dict
                                    "document_structure": structure
                                    or {},  # Garantir dict
                                }
                            )

                            # Atualizar metadados no banco
                            with self.tracer.start_as_current_span(
                                "db.update_metadata", kind=SpanKind.CLIENT
                            ) as meta_update_span:
                                meta_update_span.set_attribute(
                                    SpanAttributes.DB_SYSTEM, "postgresql"
                                )
                                meta_update_span.set_attribute(
                                    SpanAttributes.DB_OPERATION, "UPDATE"
                                )
                                meta_update_span.set_attribute(
                                    SpanAttributes.DB_SQL_TABLE, "documentos_originais"
                                )
                                meta_update_span.set_attribute(
                                    "db.document_id", document.id
                                )
                                try:
                                    DocumentoRepository.atualizar_metadados(
                                        document.id, document.metadata
                                    )
                                    meta_update_span.set_status(Status(StatusCode.OK))
                                except Exception as db_meta_exc:
                                    meta_update_span.record_exception(db_meta_exc)
                                    meta_update_span.set_status(
                                        Status(StatusCode.ERROR, str(db_meta_exc))
                                    )
                                    logger.warning(
                                        f"Falha ao atualizar metadados no DB para doc {document.id}: {db_meta_exc}"
                                    )  # Logar, mas não parar o processo?

                        else:
                            # Registrar erro de tipo não suportado
                            extraction_actual_span.set_status(
                                Status(
                                    StatusCode.ERROR,
                                    f"Tipo de arquivo não suportado: {file_type}",
                                )
                            )
                            record_document_processing(
                                "error_unsupported_type", file_type
                            )

                            # Para outros tipos de arquivo (implementação futura)
                            raise DocumentProcessingError(
                                f"Tipo de arquivo não suportado: {file_type}"
                            )

                        extraction_time = time.time() - extraction_start
                        record_extraction_time(
                            extraction_time, document.file_type
                        )  # Métrica
                        extraction_actual_span.set_attribute(
                            "duration_ms", int(extraction_time * 1000)
                        )
                        record_document_processing(
                            "success_extraction", document.file_type
                        )  # Métrica

                    except Exception as e:
                        extraction_actual_span.record_exception(e)
                        extraction_actual_span.set_status(
                            Status(StatusCode.ERROR, str(e))
                        )
                        raise  # Relançar

                span.set_attribute("document.extracted_text_length", len(text))

                # 4. Determinar a melhor estratégia de chunking se estiver configurado como "auto"
                if chunk_strategy == "auto":
                    suggested_strategy = self._determine_document_type(
                        file_name, document.metadata
                    )
                    logger.info(
                        f"Estratégia de chunking sugerida para {file_name}: {suggested_strategy}"
                    )
                    span.set_attribute(
                        "document.chunk_strategy_effective", suggested_strategy
                    )
                else:
                    span.set_attribute(
                        "document.chunk_strategy_effective", chunk_strategy
                    )

                # 5. Chunking com a estratégia selecionada
                chunk_size = self.settings.CHUNK_SIZE
                chunk_overlap = self.settings.CHUNK_OVERLAP
                chunking_start = time.time()

                chunks = create_semantic_chunks(
                    text,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    strategy=suggested_strategy,
                )

                chunking_time = time.time() - chunking_start

                if not chunks:
                    # Registrar erro de chunking
                    record_document_processing("warning_no_chunks", file_type)
                    logger.warning(f"Nenhum chunk extraído do documento {file_name}")
                    span.set_attribute("document.no_chunks_extracted", True)
                    span.set_status(
                        Status(
                            StatusCode.OK,
                            "Processamento concluído, mas sem chunks gerados.",
                        )
                    )
                    document.processed = (
                        False  # Marcar como não processado (sem chunks)
                    )
                    return document

                # 6. Avaliar qualidade dos chunks
                quality_metrics = evaluate_chunk_quality(chunks, text)

                # Registrar métricas de qualidade
                record_chunking_quality(
                    quality_metrics[
                        "avg_coherence"
                    ],  # Assumindo que avg_coherence é o score principal
                    suggested_strategy,
                    file_type,
                )

                logger.info(
                    f"Chunking concluído para {file_name}. "
                    f"Estratégia: {suggested_strategy}, "
                    f"Chunks: {len(chunks)}, "
                    f"Qualidade: {quality_metrics}"
                )

                # Registra distrinuição de tamanho de chunks
                for chunk in chunks:
                    record_chunk_size(len(chunk), "chars")
                    record_chunk_size(len(chunk.split()), "tokens")

                # 7. Gerar embeddings em lote para os chunks
                embeddings = self.embedding_service.embed_batch(chunks)

                # 6. Criar e armazenar chunks no banco de dados
                chunks_data = []
                for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
                    # Adicionar score de qualidade aos metadados do chunk
                    chunk_metadata = {
                        "documento": file_name,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "texto_tamanho": len(chunk_text),
                        "chunking_strategy": suggested_strategy,
                        "chunk_quality_coherence": quality_metrics.get(
                            "avg_coherence"
                        ),  # Salvar score específico
                        # Adicionar outros scores se houver: quality_metrics.get('avg_separation') etc.
                    }
                    chunk_data = {
                        "documento_id": document.id,
                        "texto": chunk_text,
                        "embedding": embedding,
                        "pagina": None,  # Implementação futura: mapear para páginas
                        "posicao": i,
                        "metadados": chunk_metadata,
                    }
                    chunks_data.append(chunk_data)

                successful_chunks = ChunkRepository.criar_chunks_em_lote(chunks_data)
                document.chunks_count = successful_chunks
                document.processed = successful_chunks > 0

                # Registrar sucesso no processamento completo
                record_document_processing(
                    "success_complete", file_type
                )  # Usar função auxiliar

                processing_time = time.time() - processing_start
                logger.info(
                    f"Documento {file_name} processado com sucesso: {successful_chunks} chunks criados"
                    f"{successful_chunks} chunks criados em {processing_time:.2f}s "
                    f"usando estratégia {suggested_strategy}"
                )

                span.set_attribute("document.chunks_count_initial", len(chunks))
                span.set_attribute(
                    "document.avg_chunk_length",
                    sum(len(ct) for ct in chunks) / max(1, len(chunks)),
                )
                span.set_attribute("document.chunks_saved_count", successful_chunks)
                span.set_attribute("document.processed_status", document.processed)

                processing_time = time.time() - processing_start
                span.set_attribute("duration_ms", int(processing_time * 1000))
                span.set_status(
                    Status(StatusCode.OK)
                )  # Marcar OK no span principal se chegou até aqui

                return document

            except Exception as e:
                processing_time = (
                    time.time() - processing_start
                )  # Calcular tempo mesmo em erro
                logger.error(
                    f"Erro ao processar documento {file_name} (ID: {db_document_id}): {e}",
                    exc_info=True,
                )
                # Registrar erro no span principal
                span.set_attribute("duration_ms", int(processing_time * 1000))
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, description=str(e)))
                span.set_attribute("error.type", type(e).__name__)
                # Métrica Prometheus (manter)
                record_document_processing("error_processing", file_type)
                # Relançar exceção específica do serviço
                raise DocumentProcessingError(
                    f"Erro ao processar documento {file_name}: {str(e)}"
                ) from e

    @track_timing
    async def get_document(self, document_id: int) -> Optional[Document]:
        """
        Obtém um documento pelo ID.

        Args:
            document_id: ID do documento

        Returns:
            Document: Documento encontrado, ou None se não existir
        """
        with self.tracer.start_as_current_span(
            "document_service.get_document", kind=SpanKind.SERVER
        ) as span:
            span.set_attribute("db.document_id", document_id)
            try:
                # Assumir que a chamada ao repositório é rápida ou instrumentada internamente
                db_document = DocumentoRepository.obter_por_id(document_id)
                if not db_document:
                    span.set_attribute("result.found", False)
                    span.set_status(Status(StatusCode.OK, "Documento não encontrado"))
                    return None
                else:
                    span.set_attribute("result.found", True)
                    span.set_status(Status(StatusCode.OK))
                    # A conversão from_db_model geralmente é rápida
                    return Document.from_db_model(db_document)
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    @track_timing
    async def list_documents(self, include_content: bool = False) -> List[Document]:
        """
        Lista todos os documentos.

        Args:
            include_content: Se True, inclui o conteúdo binário

        Returns:
            list: Lista de documentos
        """
        with self.tracer.start_as_current_span(
            "document_service.list_documents", kind=SpanKind.SERVER
        ) as span:
            span.set_attribute("param.include_content", include_content)
            try:
                db_documents = DocumentoRepository.listar_todos(
                    incluir_conteudo=include_content
                )
                span.set_attribute("results.count", len(db_documents))
                span.set_status(Status(StatusCode.OK))
                return [Document.from_db_model(doc) for doc in db_documents]
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    @track_timing
    async def delete_document(self, document_id: int) -> bool:
        """
        Exclui um documento pelo ID.

        Args:
            document_id: ID do documento

        Returns:
            bool: True se excluído com sucesso, False caso contrário
        """
        with self.tracer.start_as_current_span(
            "document_service.delete_document", kind=SpanKind.SERVER
        ) as span:
            span.set_attribute("db.document_id", document_id)
            try:
                deleted = DocumentoRepository.excluir_documento(document_id)
                span.set_attribute("result.deleted", deleted)
                span.set_status(Status(StatusCode.OK))
                return deleted
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    @track_timing
    async def search_documents(self, query: str) -> List[Document]:
        """
        Busca documentos por nome ou conteúdo.

        Args:
            query: Texto para busca

        Returns:
            list: Lista de documentos encontrados
        """
        with self.tracer.start_as_current_span(
            "document_service.search_documents", kind=SpanKind.SERVER
        ) as span:
            span.set_attribute("param.query", query)
            try:
                db_documents = DocumentoRepository.buscar_por_nome(query)
                span.set_attribute("results.count", len(db_documents))
                span.set_status(Status(StatusCode.OK))
                return [Document.from_db_model(doc) for doc in db_documents]
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise


# Instância singleton
_document_service_instance: Optional[DocumentService] = None


def get_document_service() -> DocumentService:
    """
    Retorna a instância do serviço de documentos.

    Returns:
        DocumentService: Instância do serviço
    """
    global _document_service_instance

    if _document_service_instance is None:
        _document_service_instance = DocumentService()

    return _document_service_instance
