# teste_chunking.py
import logging
import argparse
import time
from pathlib import Path
from typing import List, Dict, Any
from processors.chunkers.semantic_chunker import create_semantic_chunks, evaluate_chunk_quality
from processors.extractors.pdf_extractor import PDFExtractor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def testar_estrategias_chunking(arquivo_path: str, tamanho_chunk: int = 800, sobreposicao: int = 100):
    """
    Testa diferentes estratégias de chunking em um documento e compara os resultados.
    
    Args:
        arquivo_path: Caminho para o arquivo PDF
        tamanho_chunk: Tamanho máximo do chunk
        sobreposicao: Sobreposição entre chunks
    """
    try:
        # Carregar o documento
        with open(arquivo_path, 'rb') as f:
            conteudo_binario = f.read()
        
        # Extrair texto
        logger.info(f"Extraindo texto de {arquivo_path}")
        texto, metadados, estrutura = PDFExtractor.extract_all(conteudo_binario)
        
        # Nome do arquivo para exibição
        nome_arquivo = Path(arquivo_path).name
        
        # Testar cada estratégia
        estrategias = ["auto", "header_based", "paragraph", "hybrid"]
        resultados = {}
        
        for estrategia in estrategias:
            logger.info(f"Testando estratégia: {estrategia}")
            inicio = time.time()
            
            # Criar chunks com a estratégia atual
            chunks = create_semantic_chunks(
                texto, 
                chunk_size=tamanho_chunk, 
                chunk_overlap=sobreposicao,
                strategy=estrategia
            )
            
            duracao = time.time() - inicio
            
            # Avaliar qualidade
            metricas = evaluate_chunk_quality(chunks, texto)
            
            # Calcular distribuição de tamanho
            tamanhos = [len(chunk) for chunk in chunks]
            tamanho_medio = sum(tamanhos) / max(1, len(chunks))
            variacao = max(tamanhos) - min(tamanhos) if chunks else 0
            
            # Calcular mínimo, máximo e quartis para análise estatística
            tamanhos.sort()
            min_tamanho = tamanhos[0] if chunks else 0
            max_tamanho = tamanhos[-1] if chunks else 0
            quartil_1 = tamanhos[len(tamanhos)//4] if len(chunks) >= 4 else min_tamanho
            mediana = tamanhos[len(tamanhos)//2] if chunks else 0
            quartil_3 = tamanhos[3*len(tamanhos)//4] if len(chunks) >= 4 else max_tamanho
            
            # Guardar resultados
            resultados[estrategia] = {
                "num_chunks": len(chunks),
                "tempo_processamento": duracao,
                "metricas_qualidade": metricas,
                "tamanho_medio": tamanho_medio,
                "variacao": variacao,
                "estatisticas": {
                    "min": min_tamanho,
                    "q1": quartil_1,
                    "mediana": mediana,
                    "q3": quartil_3,
                    "max": max_tamanho
                }
            }
        
        # Exibir resultados comparativos
        print("\n" + "="*80)
        print(f"RESULTADOS PARA: {nome_arquivo}")
        print("="*80)
        
        # Tabela principal de resultados
        print(f"{'Estratégia':<15} {'Chunks':<8} {'Tempo (s)':<10} {'Coerência':<10} {'Tamanho Médio':<15} {'Variação':<10}")
        print("-"*80)
        
        for estrategia, resultado in resultados.items():
            print(
                f"{estrategia:<15} "
                f"{resultado['num_chunks']:<8} "
                f"{resultado['tempo_processamento']:.2f}s{'':5} "
                f"{resultado['metricas_qualidade']['avg_coherence']:.2f}{'':6} "
                f"{int(resultado['tamanho_medio']):<15} "
                f"{int(resultado['variacao']):<10}"
            )
        
        # Tabela de métricas detalhadas de qualidade
        print("\n" + "-"*80)
        print("MÉTRICAS DE QUALIDADE DETALHADAS")
        print("-"*80)
        print(f"{'Estratégia':<15} {'Coerência':<10} {'Cobertura':<10} {'Consistência':<12}")
        print("-"*80)
        
        for estrategia, resultado in resultados.items():
            metricas = resultado['metricas_qualidade']
            print(
                f"{estrategia:<15} "
                f"{metricas['avg_coherence']:.2f}{'':6} "
                f"{metricas['coverage']:.2f}{'':6} "
                f"{metricas['size_consistency']:.2f}{'':8} "
            )
        
        # Estatísticas de distribuição de tamanho
        print("\n" + "-"*80)
        print("DISTRIBUIÇÃO DE TAMANHO DOS CHUNKS (caracteres)")
        print("-"*80)
        print(f"{'Estratégia':<15} {'Mínimo':<8} {'Q1':<8} {'Mediana':<8} {'Q3':<8} {'Máximo':<8}")
        print("-"*80)
        
        for estrategia, resultado in resultados.items():
            estatisticas = resultado['estatisticas']
            print(
                f"{estrategia:<15} "
                f"{estatisticas['min']:<8} "
                f"{estatisticas['q1']:<8} "
                f"{estatisticas['mediana']:<8} "
                f"{estatisticas['q3']:<8} "
                f"{estatisticas['max']:<8} "
            )
        
        print("\nRecomendação:")
        # Algoritmo aprimorado para recomendar uma estratégia
        melhores = sorted(
            estrategias, 
            key=lambda e: (
                resultados[e]['metricas_qualidade']['avg_coherence'] * 0.5 + 
                resultados[e]['metricas_qualidade']['coverage'] * 0.3 +
                resultados[e]['metricas_qualidade']['size_consistency'] * 0.2
            ),
            reverse=True
        )
        
        print(f"Para este documento, a estratégia recomendada é: {melhores[0]}")
        print("="*80 + "\n")
        
        return resultados
        
    except Exception as e:
        logger.error(f"Erro ao testar estratégias: {e}")
        return {}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Teste de estratégias de chunking")
    parser.add_argument("arquivo", help="Caminho para o arquivo PDF a ser testado")
    parser.add_argument("--tamanho", type=int, default=800, help="Tamanho máximo do chunk")
    parser.add_argument("--sobreposicao", type=int, default=100, help="Sobreposição entre chunks")
    parser.add_argument("--detalhe", action="store_true", help="Mostrar análise detalhada")
    
    args = parser.parse_args()
    
    testar_estrategias_chunking(args.arquivo, args.tamanho, args.sobreposicao)
