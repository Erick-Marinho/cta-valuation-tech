import logging
from typing import List, Optional, Tuple
import json # Necessário para lidar com a desserialização inicial

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, delete as sqlalchemy_delete # Importar delete
from sqlmodel import select # Usar select do SQLModel/SQLAlchemy

# Importar interface do domínio e entidades/VOs do domínio
from domain.repositories.document_repository import DocumentRepository
from domain.aggregates.document.document import Document
from domain.aggregates.document.document_metadata import DocumentMetadata # <-- Adicionar import

# Importar modelo SQLModel do banco
from infrastructure.persistence.sqlmodel.models import DocumentoDB

logger = logging.getLogger(__name__)

class SqlModelDocumentRepository(DocumentRepository):
    """ Implementação do DocumentRepository usando SQLModel e AsyncSession. """

    def __init__(self, session: AsyncSession):
        self._session = session

    # --- Funções Auxiliares de Mapeamento ---

    def _map_db_to_domain(self, db_doc: Optional[DocumentoDB]) -> Optional[Document]:
        """ Mapeia o modelo SQLModel (DB) para a entidade do domínio. """
        if db_doc is None:
            logger.debug("_map_db_to_domain recebeu db_doc=None")
            return None

        logger.debug(f"Mapeando DocumentoDB ID: {db_doc.id}, Nome: {db_doc.nome_arquivo}")
        metadata_vo = DocumentMetadata() # Default vazio
        try:
            metadata_from_db = db_doc.metadados
            logger.debug(f"Metadados brutos do DB (tipo {type(metadata_from_db)}): {metadata_from_db}")

            metadata_dict = {}
            if isinstance(metadata_from_db, str):
                try:
                    metadata_dict = json.loads(metadata_from_db)
                    logger.debug("Metadados decodificados de string JSON com sucesso.")
                except json.JSONDecodeError:
                    logger.error(f"Falha ao decodificar JSON de metadados para doc ID {db_doc.id}: '{metadata_from_db}'")
                    metadata_dict = {"error": "invalid_metadata_format", "raw_content": metadata_from_db}
            elif isinstance(metadata_from_db, dict):
                 metadata_dict = metadata_from_db
                 logger.debug("Metadados já eram um dicionário.")
            elif metadata_from_db is not None: # Lidar com outros tipos inesperados
                 logger.warning(f"Metadados do DB não são string nem dict para doc ID {db_doc.id} (tipo: {type(metadata_from_db)}). Usando dict vazio.")

            if metadata_dict:
                 # Criar o VO a partir do dicionário
                 metadata_vo = DocumentMetadata.from_dict(metadata_dict) # <-- MUDANÇA: Criar VO
                 logger.debug(f"DocumentMetadata VO criado a partir do dicionário para doc ID {db_doc.id}")

            domain_document = Document(
                id=db_doc.id,
                name=db_doc.nome_arquivo,
                file_type=db_doc.tipo_arquivo,
                upload_date=db_doc.data_upload,
                metadata=metadata_vo, # <-- MUDANÇA: Atribuir o VO
                size_kb=db_doc.size_kb if db_doc.size_kb is not None else 0.0,
                chunks_count=db_doc.chunks_count if db_doc.chunks_count is not None else 0,
                processed=db_doc.processed if db_doc.processed is not None else False,
            )
            logger.debug(f"Mapeamento para Document (domínio) bem-sucedido para ID: {domain_document.id}")
            return domain_document

        except Exception as e:
             # Logar o erro específico durante a criação do Document ou DocumentMetadata
             logger.exception(f"Erro INESPERADO durante _map_db_to_domain para ID {db_doc.id if db_doc else 'N/A'}: {e}")
             # Pode ser útil retornar um Document com metadados indicando erro de carregamento
             # return Document(id=db_doc.id, name=db_doc.nome_arquivo, metadata=DocumentMetadata(additional_properties={"load_error": str(e)}))
             return None # Ou retornar None para indicar falha completa no mapeamento

    # _map_domain_to_db não é mais necessário se fizermos o mapeamento direto no save

    # --- Implementação dos Métodos do Repositório ---

    async def save(self, document: Document) -> Document:
        """ Salva (cria ou atualiza) um documento usando SQLModel. """
        try:
            # Converter metadata VO para dict ANTES de interagir com o DB
            metadata_dict = document.metadata.to_dict() if document.metadata else {} # <-- MUDANÇA: Usar to_dict()

            if document.id:
                # Atualizar
                db_doc = await self._session.get(DocumentoDB, document.id)
                if db_doc:
                    db_doc.nome_arquivo = document.name
                    db_doc.tipo_arquivo = document.file_type
                    db_doc.data_upload = document.upload_date # Geralmente não se atualiza, mas ok
                    db_doc.metadados = metadata_dict # <-- MUDANÇA: Atribuir dict
                    db_doc.size_kb = document.size_kb
                    db_doc.chunks_count = document.chunks_count
                    db_doc.processed = document.processed
                    logger.debug(f"Preparando para atualizar DocumentoDB ID: {document.id}")
                else:
                    logger.error(f"Tentativa de atualizar DocumentoDB ID {document.id} que não existe.")
                    raise ValueError(f"Documento com ID {document.id} não encontrado para atualização.")
            else:
                # Inserir
                db_doc = DocumentoDB(
                    # id=None, será gerado pelo DB
                    nome_arquivo=document.name,
                    tipo_arquivo=document.file_type,
                    data_upload=document.upload_date,
                    metadados=metadata_dict, # <-- MUDANÇA: Atribuir dict
                    size_kb=document.size_kb,
                    chunks_count=document.chunks_count,
                    processed=document.processed,
                )
                self._session.add(db_doc)
                logger.debug(f"Preparando para inserir novo DocumentoDB: {document.name}")

            await self._session.commit()
            await self._session.refresh(db_doc)
            logger.info(f"Documento salvo com ID: {db_doc.id} (SizeKB: {db_doc.size_kb:.2f}, Chunks: {db_doc.chunks_count}, Processed: {db_doc.processed})")

            # Mapear de volta para o domínio para retornar o estado atualizado (já com o ID)
            # _map_db_to_domain agora lida com a conversão para VO
            return self._map_db_to_domain(db_doc)

        except Exception as e:
            logger.exception(f"Erro ao salvar documento (ID: {document.id}, Nome: {document.name}): {e}")
            await self._session.rollback()
            raise

    async def find_by_id(self, document_id: int) -> Optional[Document]:
        """ Busca um documento pelo ID usando SQLModel. """
        # Código anterior com prints de debug removido para clareza
        try:
            # Usar .get() é mais direto para buscar por PK
            db_doc = await self._session.get(DocumentoDB, document_id)
            if db_doc:
                logger.debug(f"DocumentoDB ID {document_id} encontrado.")
                return self._map_db_to_domain(db_doc)
            else:
                logger.debug(f"DocumentoDB ID {document_id} não encontrado.")
                return None
        except Exception as e:
             logger.exception(f"Erro ao buscar documento por ID {document_id}: {e}")
             return None

    async def find_all(self, limit: int = 100, offset: int = 0) -> List[Document]:
         """ Lista documentos com paginação usando SQLModel. """
         try:
             statement = select(DocumentoDB).offset(offset).limit(limit).order_by(DocumentoDB.data_upload.desc())
             results = await self._session.execute(statement)
             db_docs: List[DocumentoDB] = results.scalars().all()
             logger.debug(f"Busca find_all (limit={limit}, offset={offset}) retornou {len(db_docs)} objetos DocumentoDB.")
             # _map_db_to_domain lida com a conversão para VO
             domain_docs = [domain_doc for db_doc in db_docs if (domain_doc := self._map_db_to_domain(db_doc)) is not None]
             logger.debug(f"Após mapeamento, {len(domain_docs)} documentos de domínio foram criados.")
             return domain_docs
         except Exception as e:
            logger.exception(f"Erro ao buscar todos os documentos (limit={limit}, offset={offset}): {e}")
            return []

    async def delete(self, document_id: int) -> bool:
        """ Exclui um documento pelo ID usando SQLModel. """
        try:
            # Usar delete do SQLAlchemy para eficiência
            statement = sqlalchemy_delete(DocumentoDB).where(DocumentoDB.id == document_id)
            result = await self._session.execute(statement)
            await self._session.commit()
            deleted_count = result.rowcount
            if deleted_count > 0:
                 logger.info(f"Documento ID {document_id} excluído com sucesso ({deleted_count} linha(s) afetada(s)).")
                 return True
            else:
                 logger.warning(f"Nenhum documento encontrado com ID {document_id} para excluir.")
                 return False # Documento não existia
        except Exception as e:
            logger.exception(f"Erro ao excluir documento ID {document_id}: {e}")
            await self._session.rollback()
            return False # Falha na exclusão

    async def count_all(self) -> int:
        """ Conta todos os documentos usando SQLModel. """
        try:
            statement = select(func.count(DocumentoDB.id))
            results = await self._session.execute(statement)
            count = results.scalar_one_or_none()
            logger.debug(f"Contagem total de documentos retornou: {count}")
            return count if count is not None else 0
        except Exception as e:
            logger.exception(f"Erro ao contar todos os documentos: {e}")
            return 0
