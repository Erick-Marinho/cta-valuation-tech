import sys
import os
import logging
from pathlib import Path

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Adicionar o diretório raiz ao PYTHONPATH
current_dir = Path(__file__).parent.parent # Ajustar para apontar para 'backend'
root_dir = current_dir.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(current_dir)) # Adicionar também o dir atual se necessário

# Importar após ajustar o path
# --- Imports Corrigidos/Removidos ---
# from db.connection import execute_query, get_connection # REMOVER - Usar SQLAlchemy
# Importar interfaces/implementações necessárias para instanciar manualmente
from application.interfaces.embedding_provider import EmbeddingProvider
# Ex: from interface.api.dependencies import get_embedding_provider # Para obter a função
# Ex: from infrastructure.external_services.embedding.huggingface_embedding_provider import HuggingFaceEmbeddingProvider
# from db.queries.hybrid_search import realizar_busca_hibrida # REMOVER - Lógica antiga
from config.config import get_settings # Corrigido: de config.config
# --- Fim Imports Corrigidos/Removidos ---

async def diagnosticar_sistema_rag():
    """Script para diagnosticar problemas no sistema RAG."""
    print("====== DIAGNÓSTICO DO SISTEMA RAG (REQUER REFAATORAÇÃO) ======")
    print("!!! ATENÇÃO: Este script está desatualizado e precisa ser refatorado para usar SQLAlchemy/SQLModel e a nova arquitetura de serviços/repositórios. !!!")

    settings = get_settings()

    # 1. Verificar conexão com o banco de dados (USANDO SQLALCHEMY)
    print("\n[1] Verificando conexão com o banco de dados via SQLAlchemy...")
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        async with engine.connect() as connection:
             result = await connection.execute(text("SELECT 1"))
             if result.scalar_one() == 1:
                 print("✅ Conexão com o banco de dados (SQLAlchemy) funcionando.")
             else:
                 print("❌ Problema na execução de consulta simples via SQLAlchemy.")
                 return
        await engine.dispose() # Fechar engine
    except Exception as e:
        print(f"❌ Erro ao conectar/consultar via SQLAlchemy: {str(e)}")
        print(f"   Verifique DATABASE_URL: {settings.DATABASE_URL}")
        return

    # 2. Verificar quantidade de documentos e chunks (USANDO SQLALCHEMY)
    print("\n[2] Verificando documentos e chunks (SQLAlchemy)...")
    try:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        async with engine.connect() as connection:
             doc_count_res = await connection.execute(text("SELECT COUNT(*) FROM documentos_originais"))
             doc_count = doc_count_res.scalar_one()
             chunk_count_res = await connection.execute(text("SELECT COUNT(*) FROM chunks_vetorizados"))
             chunk_count = chunk_count_res.scalar_one()
             print(f"📚 Total de documentos: {doc_count}")
             print(f"📝 Total de chunks: {chunk_count}")
             if doc_count == 0 or chunk_count == 0:
                  print("⚠️ Banco de dados contém poucos ou nenhum documento/chunk.")
        await engine.dispose()
    except Exception as e:
        print(f"❌ Erro ao verificar contagens via SQLAlchemy: {str(e)}")
        # return # Pode continuar mesmo com erro aqui

    # --- Seções 3, 4, 5 (Busca Híbrida, Análise de Código) estão OBSOLETAS ---
    print("\n[3] Teste de busca (OBSOLETO - requer ChunkRepository.find_similar)")
    print("[4] Análise de implementação (OBSOLETO)")

    print("\nDiagnóstico básico concluído. Funcionalidade de busca precisa ser testada via API ou scripts de avaliação refatorados.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(diagnosticar_sistema_rag())
