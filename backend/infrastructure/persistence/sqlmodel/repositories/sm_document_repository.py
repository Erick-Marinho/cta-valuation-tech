import logging
from typing import List, Optional, Tuple
import json # Ainda precisamos para o erro de decoding no mapeamento (leitura)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func # Para count
from sqlmodel import select # Usar select do SQLModel/SQLAlchemy

# Importar interface do domínio e entidade do domínio
from domain.repositories.document_repository import DocumentRepository
from domain.aggregates.document.document import Document

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
        try:
            metadata_dict = {}
            metadata_from_db = db_doc.metadados
            logger.debug(f"Metadados brutos do DB (tipo {type(metadata_from_db)}): {metadata_from_db}")

            if isinstance(metadata_from_db, str):
                try:
                    metadata_dict = json.loads(metadata_from_db)
                    logger.debug("Metadados decodificados de string JSON com sucesso.")
                except json.JSONDecodeError:
                    logger.error(f"Falha ao decodificar JSON de metadados para doc ID {db_doc.id}: '{metadata_from_db}'")
                    metadata_dict = {"error": "invalid_metadata_format"}
            elif isinstance(metadata_from_db, dict):
                 metadata_dict = metadata_from_db
                 logger.debug("Metadados já eram um dicionário.")
            else:
                 logger.warning(f"Metadados do DB não são string nem dict para doc ID {db_doc.id} (tipo: {type(metadata_from_db)}). Usando dict vazio.")

            # Criar entidade do domínio lendo os novos campos do DB
            domain_document = Document(
                id=db_doc.id,
                name=db_doc.nome_arquivo,
                file_type=db_doc.tipo_arquivo,
                upload_date=db_doc.data_upload,
                metadata=metadata_dict,
                # Ler os novos campos do objeto db_doc
                size_kb=db_doc.size_kb if db_doc.size_kb is not None else 0.0,
                chunks_count=db_doc.chunks_count if db_doc.chunks_count is not None else 0,
                processed=db_doc.processed if db_doc.processed is not None else False,
                # O conteúdo binário não é lido aqui por padrão
            )
            logger.debug(f"Mapeamento para Document (domínio) bem-sucedido para ID: {domain_document.id}")
            return domain_document

        except Exception as e:
             logger.exception(f"Erro INESPERADO durante _map_db_to_domain para ID {db_doc.id if db_doc else 'N/A'}: {e}")
             return None

    def _map_domain_to_db(self, domain_doc: Document) -> DocumentoDB:
        """ Mapeia a entidade do domínio para o modelo SQLModel (DB). """
        # Incluir os novos campos no mapeamento para inserção/atualização
        return DocumentoDB(
            id=domain_doc.id,
            nome_arquivo=domain_doc.name,
            tipo_arquivo=domain_doc.file_type,
            data_upload=domain_doc.upload_date,
            metadados=domain_doc.metadata,
            # Mapear os novos campos
            size_kb=domain_doc.size_kb,
            chunks_count=domain_doc.chunks_count,
            processed=domain_doc.processed,
            # conteudo_binario não é mapeado aqui
        )

    # --- Implementação dos Métodos do Repositório ---

    async def save(self, document: Document) -> Document:
        """ Salva (cria ou atualiza) um documento usando SQLModel. """
        try:
            if document.id:
                # Atualizar: Obter o objeto existente do DB
                db_doc = await self._session.get(DocumentoDB, document.id)
                if db_doc:
                    # Atualizar os campos do objeto existente a partir do domínio
                    db_doc.nome_arquivo = document.name
                    db_doc.tipo_arquivo = document.file_type
                    db_doc.data_upload = document.upload_date
                    db_doc.metadados = document.metadata
                    # Atualizar os novos campos
                    db_doc.size_kb = document.size_kb
                    db_doc.chunks_count = document.chunks_count
                    db_doc.processed = document.processed
                    # conteudo_binario não é atualizado aqui
                    logger.debug(f"Preparando para atualizar DocumentoDB ID: {document.id}")
                else:
                    # Documento com ID fornecido não encontrado para atualização
                    # Poderia lançar um erro ou tratar como inserção? Lançar erro é mais seguro.
                    logger.error(f"Tentativa de atualizar DocumentoDB ID {document.id} que não existe.")
                    raise ValueError(f"Documento com ID {document.id} não encontrado para atualização.")
            else:
                # Inserir: Criar um novo objeto DB a partir do domínio (usando _map_domain_to_db atualizado)
                db_doc = self._map_domain_to_db(document)
                self._session.add(db_doc)
                logger.debug(f"Preparando para inserir novo DocumentoDB: {document.name}")

            await self._session.commit() # Salva as mudanças (INSERT ou UPDATE)
            await self._session.refresh(db_doc) # Atualiza o objeto db_doc com dados do DB (ex: ID gerado)
            logger.info(f"Documento salvo com ID: {db_doc.id} (SizeKB: {db_doc.size_kb:.2f}, Chunks: {db_doc.chunks_count}, Processed: {db_doc.processed})")

            # Retornar a entidade do domínio mapeada a partir do objeto DB atualizado/criado
            return self._map_db_to_domain(db_doc)

        except Exception as e:
            logger.exception(f"Erro ao salvar documento (ID: {document.id}, Nome: {document.name}): {e}")
            await self._session.rollback() # Desfazer transação em caso de erro
            raise # Relançar a exceção

    async def find_by_id(self, document_id: int) -> Optional[Document]:
        """ Busca um documento pelo ID usando SQLModel. """
        print(f"\n[DEBUG PRINT] find_by_id: Buscando ID {document_id}")
        try:
            statement = select(DocumentoDB).where(DocumentoDB.id == document_id)
            results = await self._session.execute(statement)
            db_doc = results.first()

            # --- Adicionar Prints para Diagnóstico ---
            if db_doc:
                 print(f"[DEBUG PRINT] find_by_id: results.first() retornou um objeto!")
                 print(f"[DEBUG PRINT] find_by_id: Tipo do objeto: {type(db_doc)}")
                 # Tentar acessar alguns atributos básicos
                 try:
                      print(f"[DEBUG PRINT] find_by_id: db_doc[0].id = {db_doc[0].id}")
                      print(f"[DEBUG PRINT] find_by_id: db_doc[0].nome_arquivo = {db_doc[0].nome_arquivo}")
                      # Acessar metadados pode ser problemático se for a causa do erro
                      # print(f"[DEBUG PRINT] find_by_id: db_doc[0].metadados = {db_doc[0].metadados}")
                      print(f"[DEBUG PRINT] find_by_id: db_doc[0].size_kb = {getattr(db_doc[0], 'size_kb', 'N/A')}")
                 except Exception as access_err:
                      print(f"[DEBUG PRINT] find_by_id: Erro ao acessar atributos de db_doc[0]: {access_err}")
            else:
                 print(f"[DEBUG PRINT] find_by_id: results.first() retornou None.")
            # ---------------------------------------

            # Chamar o mapeamento (se db_doc não for None)
            return self._map_db_to_domain(db_doc[0] if db_doc else None) # results.first() retorna uma tupla

        except Exception as e:
             print(f"[DEBUG PRINT] find_by_id: Exceção ocorreu: {e}")
             logger.exception(f"Erro ao buscar documento por ID {document_id}: {e}")
             return None

    async def find_all(self, limit: int = 100, offset: int = 0) -> List[Document]:
        """ Lista documentos com paginação usando SQLModel. """
        try:
            statement = select(DocumentoDB).offset(offset).limit(limit).order_by(DocumentoDB.data_upload.desc())
            results = await self._session.execute(statement)
            # Usar .scalars().all() para obter objetos DocumentoDB diretamente
            db_docs: List[DocumentoDB] = results.scalars().all()
            logger.debug(f"Busca find_all (limit={limit}, offset={offset}) retornou {len(db_docs)} objetos DocumentoDB.")
            # O mapeamento agora funcionará, pois db_doc será DocumentoDB
            domain_docs = [domain_doc for db_doc in db_docs if (domain_doc := self._map_db_to_domain(db_doc)) is not None]
            logger.debug(f"Após mapeamento, {len(domain_docs)} documentos de domínio foram criados.")
            return domain_docs
        except Exception as e:
            logger.exception(f"Erro ao buscar todos os documentos (limit={limit}, offset={offset}): {e}")
            return []

    async def delete(self, document_id: int) -> bool:
        """ Exclui um documento pelo ID usando SQLModel. """
        try:
            db_doc = await self._session.get(DocumentoDB, document_id)
            if db_doc:
                await self._session.delete(db_doc)
                await self._session.commit()
                logger.info(f"Documento ID {document_id} excluído com sucesso.")
                return True
            else:
                logger.warning(f"Documento ID {document_id} não encontrado para exclusão.")
                return False # Ou True, dependendo da semântica desejada para "não encontrado"
        except Exception as e:
            logger.exception(f"Erro ao excluir documento ID {document_id}: {e}")
            await self._session.rollback()
            return False # Indica falha

    async def count_all(self) -> int:
        """ Conta todos os documentos usando SQLModel. """
        try:
            # Contar diretamente na tabela
            statement = select(func.count(DocumentoDB.id))
            results = await self._session.execute(statement)
            count = results.scalar_one_or_none()
            logger.debug(f"Contagem total de documentos retornou: {count}")
            return count if count is not None else 0
        except Exception as e:
            logger.exception(f"Erro ao contar todos os documentos: {e}")
            return 0 # Retornar 0 em caso de erro
