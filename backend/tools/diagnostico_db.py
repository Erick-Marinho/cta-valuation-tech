import sys
import os
import logging
from pathlib import Path

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Adicionar o diretório raiz ao PYTHONPATH
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

# Importar após ajustar o path
from db.connection import execute_query, get_connection
from core.services.embedding_service import get_embedding_service
from db.queries.hybrid_search import realizar_busca_hibrida

async def diagnosticar_sistema_rag():
    """Script para diagnosticar problemas no sistema RAG."""
    print("====== DIAGNÓSTICO DO SISTEMA RAG ======")
    
    # 1. Verificar conexão com o banco de dados
    print("\n[1] Verificando conexão com o banco de dados...")
    try:
        # Tente executar uma consulta simples
        result = execute_query("SELECT 1 as teste")
        if result and len(result) > 0:
            print("✅ Conexão com o banco de dados funcionando corretamente.")
        else:
            print("❌ Problema na execução de consultas no banco de dados.")
            return
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco de dados: {str(e)}")
        print("   Verifique as configurações em DATABASE_URL no arquivo .env ou em config.py")
        return
    
    # 2. Verificar quantidade de documentos e chunks
    print("\n[2] Verificando documentos e chunks armazenados...")
    try:
        doc_count = execute_query("SELECT COUNT(*) as count FROM documentos_originais")
        chunk_count = execute_query("SELECT COUNT(*) as count FROM chunks_vetorizados")
        
        print(f"📚 Total de documentos: {doc_count[0]['count'] if doc_count else 0}")
        print(f"📝 Total de chunks: {chunk_count[0]['count'] if chunk_count else 0}")
        
        if not doc_count or doc_count[0]['count'] == 0:
            print("❌ Nenhum documento encontrado no banco de dados.")
            print("   Faça upload de documentos antes de realizar consultas.")
            return
            
        if not chunk_count or chunk_count[0]['count'] == 0:
            print("❌ Nenhum chunk encontrado no banco de dados.")
            print("   Verifique o processamento de documentos.")
            return
    except Exception as e:
        print(f"❌ Erro ao verificar documentos e chunks: {str(e)}")
        return
    
    # 3. Verificar chunks com menção a CTA
    print("\n[2.1] Verificando chunks com menção a CTA...")
    try:
        cta_chunks = execute_query("SELECT COUNT(*) as count FROM chunks_vetorizados WHERE texto ILIKE '%CTA%'")
        cta_full_chunks = execute_query("SELECT COUNT(*) as count FROM chunks_vetorizados WHERE texto ILIKE '%Conhecimentos Tradicionais Associados%'")
        
        print(f"🔍 Chunks com menção a 'CTA': {cta_chunks[0]['count'] if cta_chunks else 0}")
        print(f"🔍 Chunks com menção a 'Conhecimentos Tradicionais Associados': {cta_full_chunks[0]['count'] if cta_full_chunks else 0}")
    except Exception as e:
        print(f"❌ Erro ao verificar chunks com CTA: {str(e)}")
    
    # 4. Testar busca com threshold baixo
    print("\n[3] Testando busca com threshold reduzido...")
    try:
        query_test = "CTA"
        embedding_service = get_embedding_service()
        embedding = embedding_service.embed_text(query_test)
        
        chunks = realizar_busca_hibrida(
            query_text=query_test,
            query_embedding=embedding,
            limite=10,
            alpha=0.5,
            threshold=0.0  # Threshold zero para garantir resultados
        )
        
        if chunks:
            print(f"✅ Busca retornou {len(chunks)} resultados com threshold zero.")
            print("\nPrimeiros 3 resultados:")
            for i, chunk in enumerate(chunks[:3]):
                print(f"  - Score: {chunk.combined_score:.4f}, Origem: {chunk.arquivo_origem}")
                print(f"    Texto: {chunk.texto[:80]}...")
        else:
            print("❌ Busca não retornou resultados mesmo com threshold zero.")
            print("   Isso pode indicar problemas sérios com os embeddings ou com a implementação da busca híbrida.")
            
        # Testar busca expandida
        print("\n[3.1] Testando busca expandida (Conhecimentos Tradicionais Associados)...")
        expanded_query = "Conhecimentos Tradicionais Associados"
        expanded_embedding = embedding_service.embed_text(expanded_query)
        
        expanded_chunks = realizar_busca_hibrida(
            query_text=expanded_query,
            query_embedding=expanded_embedding,
            limite=10,
            alpha=0.5,
            threshold=0.0
        )
        
        if expanded_chunks:
            print(f"✅ Busca expandida retornou {len(expanded_chunks)} resultados.")
        else:
            print("❌ Busca expandida também não retornou resultados.")
            
    except Exception as e:
        print(f"❌ Erro ao testar busca: {str(e)}")
    
    # 5. Verificar a estrutura da função realizar_busca_hibrida
    print("\n[4] Analisando implementação da busca híbrida...")
    try:
        # Examinar o código de realizar_busca_hibrida
        import inspect
        hybrid_search_code = inspect.getsource(realizar_busca_hibrida)
        
        # Verificar se há problemas óbvios no código
        problemas = []
        
        if "filtered_chunks = [chunk for chunk in combined_results.values() if chunk.combined_score >= threshold]" in hybrid_search_code:
            problemas.append("⚠️ Filtro de threshold pode estar rejeitando todos os resultados.")
            print("   Recomendação: Reduza o valor de threshold ou remova temporariamente essa linha.")
        
        if not problemas:
            print("✅ Nenhum problema óbvio identificado na implementação da busca híbrida.")
        else:
            for problema in problemas:
                print(problema)
    except Exception as e:
        print(f"❌ Erro ao analisar implementação: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(diagnosticar_sistema_rag())