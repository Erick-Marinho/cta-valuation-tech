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
from processors.chunkers.semantic_chunker import create_semantic_chunks, evaluate_chunk_quality
from db.repositories.document_repository import DocumentoRepository
from db.repositories.chunk_repository import ChunkRepository
from utils.logging import track_timing
from utils.metrics_prometheus import DOCUMENT_PROCESSING_COUNT, CHUNK_SIZE_DISTRIBUTION, CHUNKING_QUALITY_METRICS

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
        self.settings = get_settings()
        self.embedding_service = get_embedding_service()
    
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
            if metadata.get("tipo_documento") in ["artigo", "técnico", "manual", "guia"]:
                return "header_based"
        
        # Padrão para PDFs
        return "hybrid"  # Estratégia mais versátil como padrão
    
    @track_timing
    async def process_document(self, file_name: str, file_content: bytes, 
                              file_type: str = "pdf",
                              metadata: Dict[str, Any] = None, chunk_strategy: str = "auto") -> Document:
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
        
        try:
            # 1. Criar instância de documento
            document = Document(
                name=file_name,
                file_type=file_type,
                content=file_content,
                metadata=metadata or {}
            )
            
            # 2. Salvar documento no banco de dados
            db_document_id = DocumentoRepository.criar_documento(
                nome_arquivo=document.name,
                tipo_arquivo=document.file_type,
                conteudo_binario=document.content,
                metadados=document.metadata
            )
            
            
            if not db_document_id:
                # Registrar erro de salvamento no banco de dados
                DOCUMENT_PROCESSING_COUNT.labels(
                    status='error-db_save',
                    file_type=file_type
                ).inc()
                
                raise DocumentProcessingError(f"Erro ao salvar documento {file_name} no banco de dados")
            
            document.id = db_document_id
            
            # 3. Extrair texto conforme o tipo de arquivo
            if document.is_pdf:
                # Extrair texto e metadados do PDF
                text, pdf_metadata, structure = PDFExtractor.extract_all(file_content)
                
                # registrar sucesso na extração
                DOCUMENT_PROCESSING_COUNT.labels(
                    status='success',
                    file_type='pdf'
                ).inc()
                
                # Atualizar metadados com informações do PDF
                document.metadata.update({
                    "pdf_metadata": pdf_metadata,
                    "document_structure": structure
                })
                
                # Atualizar metadados no banco
                DocumentoRepository.atualizar_metadados(document.id, document.metadata)
            else:
                # Registrar erro de tipo não suportado
                DOCUMENT_PROCESSING_COUNT.labels(
                    status='error-unsupported_type',
                    file_type=file_type
                ).inc()
                
                # Para outros tipos de arquivo (implementação futura)
                raise DocumentProcessingError(f"Tipo de arquivo não suportado: {file_type}")
            
            # 4. Determinar a melhor estratégia de chunking se estiver configurado como "auto"
            if chunking_strategy == "auto":
                suggested_strategy = self._determine_document_type(file_name, document.metadata)
                logger.info(f"Estratégia de chunking sugerida para {file_name}: {suggested_strategy}")
            else:
                suggested_strategy = chunking_strategy
            
            # 4. Dividir o texto em chunks
            chunk_size = self.settings.CHUNK_SIZE
            chunk_overlap = self.settings.CHUNK_OVERLAP
            
            # 5. Chunking com a estratégia selecionada
            chunks = create_semantic_chunks(
                text, 
                chunk_size=chunk_size, 
                chunk_overlap=chunk_overlap,
                strategy=suggested_strategy
            )
                        
            if not chunks:
                # Registrar erro de chunking
                DOCUMENT_PROCESSING_COUNT.labels(
                    status='warning_no_chunks',
                    file_type=file_type
                ).inc()
                
                logger.warning(f"Nenhum chunk extraído do documento {file_name}")
                return document
            
            # 6. Avaliar qualidade dos chunks
            quality_metrics = evaluate_chunk_quality(chunks, text)
            
            # Registrar métricas de qualidade
            CHUNKING_QUALITY_METRICS.labels(
                strategy=suggested_strategy,
                file_type=file_type
            ).observe(quality_metrics["avg_coherence"])
            
            logger.info(
                f"Chunking concluído para {file_name}. "
                f"Estratégia: {suggested_strategy}, "
                f"Chunks: {len(chunks)}, "
                f"Qualidade: {quality_metrics}"
            )
            
            # Registra distrinuição de tamanho de chunks
            for chunk in chunks:
                # Registro por caracteres
                CHUNK_SIZE_DISTRIBUTION.labels(
                    type='chars'
                ).observe(len(chunk))
                
                # Registro por tokens (palavras como aproximação)
                CHUNK_SIZE_DISTRIBUTION.labels(
                    type='tokens'
                ).observe(len(chunk.split()))
            
            
            # 5. Gerar embeddings em lote para os chunks
            embeddings = self.embedding_service.embed_batch(chunks)
            
            # 6. Criar e armazenar chunks no banco de dados
            chunks_data = []
            for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_data = {
                    "documento_id": document.id,
                    "texto": chunk_text,
                    "embedding": embedding,
                    "pagina": None,  # Implementação futura: mapear para páginas
                    "posicao": i,
                    "metadados": {
                        "documento": file_name,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "texto_tamanho": len(chunk_text),
                        "chunking_strategy": suggested_strategy,
                        "chunk_quality": quality_metrics["avg_coherence"]
                    }
                }
                chunks_data.append(chunk_data)
            
            successful_chunks = ChunkRepository.criar_chunks_em_lote(chunks_data)
            document.chunks_count = successful_chunks
            document.processed = successful_chunks > 0
            
            # Registrar sucesso no processamento completo
            DOCUMENT_PROCESSING_COUNT.labels(
                status='success_complete',
                file_type=file_type
            ).inc()
            
            processing_time = time.time() - processing_start            
            logger.info(
                f"Documento {file_name} processado com sucesso: {successful_chunks} chunks criados"
                f"{successful_chunks} chunks criados em {processing_time:.2f}s "
                f"usando estratégia {suggested_strategy}"
                )
            
            return document
            
        except Exception as e:
            # registrar erro genérico no processamento
            DOCUMENT_PROCESSING_COUNT.labels(
                status='error_processing',
                file_type=file_type
            ).inc()
            
            logger.error(f"Erro ao processar documento {file_name}: {str(e)}")
            raise DocumentProcessingError(f"Erro ao processar documento: {str(e)}")
    
    @track_timing
    async def get_document(self, document_id: int) -> Optional[Document]:
        """
        Obtém um documento pelo ID.
        
        Args:
            document_id: ID do documento
            
        Returns:
            Document: Documento encontrado, ou None se não existir
        """
        db_document = DocumentoRepository.obter_por_id(document_id)
        if not db_document:
            return None
            
        return Document.from_db_model(db_document)
    
    @track_timing
    async def list_documents(self, include_content: bool = False) -> List[Document]:
        """
        Lista todos os documentos.
        
        Args:
            include_content: Se True, inclui o conteúdo binário
            
        Returns:
            list: Lista de documentos
        """
        db_documents = DocumentoRepository.listar_todos(incluir_conteudo=include_content)
        return [Document.from_db_model(doc) for doc in db_documents]
    
    @track_timing
    async def delete_document(self, document_id: int) -> bool:
        """
        Exclui um documento pelo ID.
        
        Args:
            document_id: ID do documento
            
        Returns:
            bool: True se excluído com sucesso, False caso contrário
        """
        return DocumentoRepository.excluir_documento(document_id)
    
    @track_timing
    async def search_documents(self, query: str) -> List[Document]:
        """
        Busca documentos por nome ou conteúdo.
        
        Args:
            query: Texto para busca
            
        Returns:
            list: Lista de documentos encontrados
        """
        db_documents = DocumentoRepository.buscar_por_nome(query)
        return [Document.from_db_model(doc) for doc in db_documents]

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