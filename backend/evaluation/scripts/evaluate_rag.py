import asyncio
import logging
import os
import sys
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    # context_precision, # Adicionaremos depois
    # context_recall,    # Adicionaremos depois
)

# --- Configuração do Caminho ---
# Adiciona o diretório raiz do projeto (um nível acima de 'backend') ao sys.path
# Ajuste a profundidade ('../..') se a estrutura do seu projeto for diferente
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# --- Fim Configuração do Caminho ---

# Importar componentes da aplicação APÓS configurar o path
try:
    from core.services.rag_service import get_rag_service, RAGService
    from evaluation.datasets.sample_eval_set import evaluation_dataset
    # Certifique-se de que as variáveis de ambiente (DB, LLM keys) estão carregadas
    # O get_settings() dentro dos serviços deve lidar com isso se .env estiver configurado
except ImportError as e:
    print(f"Erro ao importar módulos: {e}")
    print(f"Verifique se o PYTHONPATH está correto ou execute o script da raiz do projeto.")
    print(f"PROJECT_ROOT calculado: {PROJECT_ROOT}")
    sys.exit(1)

# Configuração básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def prepare_evaluation_data(rag_service: RAGService) -> Dataset:
    """
    Prepara os dados para avaliação pelo RAGAS.

    Chama o RAGService para cada pergunta no dataset de avaliação
    e coleta as respostas geradas e os contextos recuperados.
    """
    processed_data = []
    logger.info(f"Iniciando processamento de {len(evaluation_dataset)} itens do dataset de avaliação.")

    for i, item in enumerate(evaluation_dataset):
        question = item["question"]
        ground_truth_answer = item.get("ground_truth_answer") # Usar .get para segurança

        logger.info(f"Processando item {i+1}/{len(evaluation_dataset)}: '{question[:50]}...'")

        try:
            # Chama o RAGService para obter resposta e debug info (que contém os contextos)
            result = await rag_service.process_query(
                query=question,
                include_debug_info=True # ESSENCIAL para obter os contextos
            )

            generated_answer = result.get("response", "")
            contexts = result.get("debug_info", {}).get("contexts", [])

            if not generated_answer:
                logger.warning(f"Resposta gerada vazia para a pergunta: {question}")
            if not contexts:
                 logger.warning(f"Nenhum contexto recuperado para a pergunta: {question}")

            # Monta o dicionário para RAGAS
            # Nota: RAGAS usa 'ground_truth' para a resposta esperada em answer_relevancy
            # e 'ground_truths' (plural) para os contextos esperados em context_recall.
            data_point = {
                "question": question,
                "answer": generated_answer,
                "contexts": contexts,
                "ground_truth": ground_truth_answer if ground_truth_answer else "" # RAGAS espera string
                # "ground_truths": [lista_de_textos_dos_chunks_ground_truth] # Adicionar para context_recall
            }
            processed_data.append(data_point)

        except Exception as e:
            logger.error(f"Erro ao processar a pergunta '{question}': {e}", exc_info=True)
            # Opcional: adicionar um item com erro ou pular
            processed_data.append({
                "question": question,
                "answer": f"ERRO: {e}",
                "contexts": [],
                "ground_truth": ground_truth_answer if ground_truth_answer else ""
            })

    logger.info("Dados processados. Convertendo para Dataset do Hugging Face.")
    # Converte a lista de dicionários para o formato Dataset do RAGAS
    ragas_dataset = Dataset.from_list(processed_data)
    return ragas_dataset

async def run_evaluation(ragas_dataset: Dataset):
    """
    Executa a avaliação RAGAS com as métricas selecionadas.
    """
    # Métricas a serem calculadas
    # Começaremos com faithfulness e answer_relevancy
    # Adicionaremos context_precision e context_recall quando tivermos os ground_truth contexts
    metrics_to_evaluate = [
        faithfulness,    # A resposta é fiel aos contextos?
        answer_relevancy # A resposta é relevante para a pergunta?
                           # (Usa LLM para avaliar, compara resposta com pergunta)
        # context_precision, # Quão relevantes são os contextos recuperados? (Precisa de ground_truth para pergunta)
        # context_recall,    # Quantos contextos relevantes foram recuperados? (Precisa de ground_truths [textos])
    ]

    logger.info(f"Iniciando avaliação RAGAS com as métricas: {[m.name for m in metrics_to_evaluate]}")

    # Executa a avaliação
    # Nota: Algumas métricas RAGAS (como answer_relevancy) podem fazer chamadas a LLMs (OpenAI por padrão)
    # Certifique-se de ter a chave da OpenAI configurada como variável de ambiente (OPENAI_API_KEY)
    # ou configure o RAGAS para usar outro LLM, se necessário.
    try:
        evaluation_result = evaluate(
            ragas_dataset,
            metrics=metrics_to_evaluate
        )
        logger.info("Avaliação RAGAS concluída.")
        print("\n--- Resultados da Avaliação RAGAS ---")
        print(evaluation_result)
        print("-------------------------------------\n")
        return evaluation_result
    except Exception as e:
         logger.error(f"Erro durante a avaliação RAGAS: {e}", exc_info=True)
         print(f"\nErro durante a avaliação RAGAS: {e}")
         print("Verifique se a variável de ambiente OPENAI_API_KEY está configurada,")
         print("pois algumas métricas RAGAS (ex: answer_relevancy) a utilizam por padrão.")
         return None


async def main():
    """
    Função principal para orquestrar a preparação dos dados e a avaliação.
    """
    logger.info("Obtendo instância do RAGService...")
    try:
        # Tenta inicializar o serviço. Isso pode carregar configurações, conectar ao DB, etc.
        rag_service = get_rag_service()
        # Poderíamos adicionar uma verificação rápida aqui, se RAGService tivesse um método healthcheck
        logger.info("RAGService obtido com sucesso.")
    except Exception as e:
        logger.error(f"Falha ao inicializar o RAGService: {e}", exc_info=True)
        print(f"ERRO: Não foi possível inicializar o RAGService. Verifique as configurações e logs. Erro: {e}")
        return

    prepared_dataset = await prepare_evaluation_data(rag_service)
    if prepared_dataset:
        await run_evaluation(prepared_dataset)
    else:
        logger.error("Falha ao preparar os dados para avaliação.")

if __name__ == "__main__":
    # Verifica se está executando como script principal
    # Garante que o loop de eventos asyncio seja iniciado corretamente
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExecução interrompida pelo usuário.")
    except Exception as e:
        print(f"\nErro inesperado na execução principal: {e}")
        logger.critical(f"Erro fatal na execução: {e}", exc_info=True)
