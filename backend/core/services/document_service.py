"""
Serviço para gerenciamento e processamento de documentos.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from core.config import get_settings
from core.exceptions import DocumentProcessingError
from ..models.document import Document
from .embedding_service import get_embedding_service
from processors.extractors.pdf_extractor import PDFExtractor
from processors.chunkers import create_semantic_chunks, create_nltk_chunks
from db.repositories.document_repository import DocumentoRepository
from db.repositories.chunk_repository import ChunkRepository
from utils.logging import track_timing
from utils.createJSON import create_json_from_chunks
from infra.mlflow.mlflow_utils import experiment_tracker

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
    
    @track_timing
    @experiment_tracker.log_document_processing
    async def process_document(self, file_name: str, file_content: bytes, 
                              file_type: str = "pdf",
                              metadata: Dict[str, Any] = None) -> Document:
        """
        Processa um documento completo: extrai texto, divide em chunks e gera embeddings.
        
        Args:
            file_name: Nome do arquivo
            file_content: Conteúdo binário do arquivo
            file_type: Tipo do arquivo (por padrão, pdf)
            metadata: Metadados adicionais do documento
            
        Returns:
            Document: Documento processado
        """
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
                raise DocumentProcessingError(f"Erro ao salvar documento {file_name} no banco de dados")
            
            document.id = db_document_id
            
            # 3. Extrair texto conforme o tipo de arquivo
            if document.is_pdf:
                # Extrair texto e metadados do PDF
                text, pdf_metadata, structure = PDFExtractor.extract_all(file_content)
                
                # Atualizar metadados com informações do PDF
                document.metadata.update({
                    "pdf_metadata": pdf_metadata,
                    "document_structure": structure
                })
                
                # Atualizar metadados no banco
                DocumentoRepository.atualizar_metadados(document.id, document.metadata)
            else:
                # Para outros tipos de arquivo (implementação futura)
                raise DocumentProcessingError(f"Tipo de arquivo não suportado: {file_type}")
            
            # 4. Dividir o texto em chunks
            chunk_size = self.settings.CHUNK_SIZE
            chunk_overlap = self.settings.CHUNK_OVERLAP
            
            chunks = create_semantic_chunks(text, chunk_size, chunk_overlap)
            #chunks = create_nltk_chunks(text, chunk_size, chunk_overlap)

            create_json_from_chunks(chunks, file_name)
            
            if not chunks:
                logger.warning(f"Nenhum chunk extraído do documento {file_name}")
                return document
            
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
                        "texto_tamanho": len(chunk_text)
                    }
                }
                chunks_data.append(chunk_data)
            
            successful_chunks = ChunkRepository.criar_chunks_em_lote(chunks_data)
            document.chunks_count = successful_chunks
            document.processed = successful_chunks > 0
            
            logger.info(f"Documento {file_name} processado com sucesso: {successful_chunks} chunks criados")
            
            return document
            
        except Exception as e:
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