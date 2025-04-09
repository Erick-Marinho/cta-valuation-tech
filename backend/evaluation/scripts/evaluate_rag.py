import asyncio
import logging
import os
import sys
from datasets import Dataset
# RAGAS Imports
from ragas import evaluate as ragas_evaluate # Renomeado para evitar conflito
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
# --- DeepEval Imports ---
from deepeval import evaluate as deepeval_evaluate # Renomeado para evitar conflito
from deepeval.metrics import (
    BiasMetric,
    ToxicityMetric,
    # SummarizationMetric, # Opcional
    GEval               # <<< GARANTIR QUE ESTÁ IMPORTADO
)
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
# --- End DeepEval Imports ---
# --- MLflow Import ---
import mlflow
# --- End MLflow Import ---
from collections import defaultdict # <<< Adicionar import
import re # <<< Adicionar import para regex

# --- Configuração do Caminho ---
# Adiciona o diretório raiz do projeto (um nível acima de 'backend') ao sys.path
# Ajuste a profundidade ('../..') se a estrutura do seu projeto for diferente
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# --- Fim Configuração do Caminho ---

# Importar componentes da aplicação APÓS configurar o path
try:
    # Importar o Serviço de Aplicação e talvez Interfaces/Repositórios se necessário instanciar manualmente
    from application.services.rag_service import RAGService # Importar o serviço refatorado
    # Importar dependências necessárias para instanciar RAGService manualmente
    from application.interfaces.embedding_provider import EmbeddingProvider
    from application.interfaces.llm_provider import LLMProvider
    from domain.repositories.chunk_repository import ChunkRepository
    # Importar implementações e provedores de dependência *se necessário* para instanciação manual
    # Ex: from interface.api.dependencies import get_embedding_provider, get_llm_provider, get_chunk_repository, SessionDep
    # Ex: from infrastructure.llm.providers.nvidia_provider import NvidiaProvider
    # Ex: from infrastructure.persistence.sqlmodel.repositories.sm_chunk_repository import SqlModelChunkRepository
    # Ex: from infrastructure.external_services.embedding.huggingface_embedding_provider import HuggingFaceEmbeddingProvider
    # Ex: from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    from evaluation.datasets.sample_eval_set import evaluation_dataset
    from config.config import get_settings, Settings # Corrigido: de config.config
    # Remover import do get_rag_service antigo
    # from core.services.rag_service import get_rag_service # REMOVER

except ImportError as e:
    print(f"Erro ao importar módulos: {e}")
    print(
        f"Verifique se o PYTHONPATH está correto ou execute o script da raiz do projeto."
    )
    print(f"PROJECT_ROOT calculado: {PROJECT_ROOT}")
    sys.exit(1)

# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def manually_create_rag_service(settings: Settings) -> RAGService:
    """
    Função auxiliar para instanciar RAGService e suas dependências fora do FastAPI.
    !! ISTO É UM EXEMPLO E PRECISA SER COMPLETADO !!
    """
    logger.info("Instanciando dependências manualmente para RAGService...")

    # 1. Criar Engine e SessionMaker (exemplo)
    # engine = create_async_engine(settings.DATABASE_URL, echo=False)
    # AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # 2. Instanciar Provedores e Repositórios (exemplo)
    # async with AsyncSessionFactory() as session:
        # embedding_provider = HuggingFaceEmbeddingProvider() # Ou outra implementação
        # llm_provider = NvidiaProvider() # Ou outra implementação
        # chunk_repo = SqlModelChunkRepository(session=session)

        # 3. Instanciar RAGService
        # rag_service = RAGService(
        #     embedding_provider=embedding_provider,
        #     llm_provider=llm_provider,
        #     chunk_repository=chunk_repo
        # )
        # return rag_service
    logger.error("!!! A função manually_create_rag_service precisa ser implementada corretamente !!!")
    raise NotImplementedError("Instanciação manual do RAGService não implementada.")


async def prepare_evaluation_data(rag_service: RAGService) -> Dataset:
    """
    Prepara os dados para avaliação pelo RAGAS.

    Chama o RAGService para cada pergunta no dataset de avaliação
    e coleta as respostas geradas e os contextos recuperados.
    """
    processed_data = []
    logger.info(
        f"Iniciando processamento de {len(evaluation_dataset)} itens do dataset de avaliação."
    )

    for i, item in enumerate(evaluation_dataset):
        question = item["question"]
        ground_truth_answer = item.get(
            "ground_truth_answer"
        )  # Usar .get para segurança
        ground_truth_contexts = item.get("ground_truths", [])

        logger.info(
            f"Processando item {i+1}/{len(evaluation_dataset)}: '{question[:50]}...'"
        )

        try:
            # Chama o RAGService para obter resposta e debug info (que contém os contextos)
            result = await rag_service.process_query(
                query=question,
                include_debug_info=True,  # ESSENCIAL para obter os contextos
            )

            generated_answer = result.get("response", "")
            contexts = result.get("debug_info", {}).get("contexts", [])

            if not generated_answer:
                logger.warning(f"Resposta gerada vazia para a pergunta: {question}")
            if not contexts:
                logger.warning(
                    f"Nenhum contexto recuperado para a pergunta: {question}"
                )
            if not ground_truth_contexts and item.get("reference_page") is not None:
                logger.warning(f"Nenhum contexto ground_truth encontrado no dataset para a pergunta: {question}. Context Recall pode não ser preciso.")

            # Monta o dicionário para RAGAS
            # Nota: RAGAS usa 'ground_truth' para a resposta esperada em answer_relevancy
            # e 'ground_truths' (plural) para os contextos esperados em context_recall.
            data_point = {
                "question": question,
                "answer": generated_answer,
                "contexts": contexts,
                "ground_truth": (
                    ground_truth_answer if ground_truth_answer else ""
                ),  # RAGAS espera string
                "ground_truths": ground_truth_contexts,
            }
            processed_data.append(data_point)

        except Exception as e:
            logger.error(
                f"Erro ao processar a pergunta '{question}': {e}", exc_info=True
            )
            # Opcional: adicionar um item com erro ou pular
            processed_data.append(
                {
                    "question": question,
                    "answer": f"ERRO: {e}",
                    "contexts": [],
                    "ground_truth": ground_truth_answer if ground_truth_answer else "",
                    "ground_truths": ground_truth_contexts,
                }
            )

    logger.info("Dados processados. Convertendo para Dataset do Hugging Face.")
    # Converte a lista de dicionários para o formato Dataset do RAGAS
    ragas_dataset = Dataset.from_list(processed_data)
    return ragas_dataset


def sanitize_mlflow_metric_name(name: str) -> str:
    """Substitui caracteres inválidos para nomes de métricas MLflow."""
    # Substitui espaços, parênteses por underscore
    name = re.sub(r'[ ()]', '_', name)
    # Remove caracteres inválidos restantes (exceto os permitidos: alfanuméricos, _, -, ., /)
    name = re.sub(r'[^a-zA-Z0-9_.\-/]', '', name)
    # Remove múltiplos underscores consecutivos
    name = re.sub(r'_+', '_', name)
    # Remove underscores no início ou fim
    name = name.strip('_')
    return name


async def run_evaluation(ragas_dataset: Dataset, settings: Settings):
    """
    Executa a avaliação RAGAS e DeepEval, registrando resultados no MLflow.
    """
    # === Iniciar Execução MLflow ===
    # Por padrão, o MLflow salva os dados localmente em um diretório 'mlruns'
    # na pasta onde o script é executado.
    with mlflow.start_run():
        logger.info("Execução MLflow iniciada.")

        # --- Registrar Parâmetros do Experimento ---
        try:
            # Parâmetros importantes que influenciam os resultados
            mlflow.log_param("llm_model", settings.LLM_MODEL)
            mlflow.log_param("embedding_model", settings.EMBEDDING_MODEL)
            mlflow.log_param("ragas_version", ragas_evaluate.__globals__.get('__version__', 'unknown')) # Tenta obter versão do Ragas
            mlflow.log_param("deepeval_version", deepeval_evaluate.__globals__.get('__version__', 'unknown')) # Tenta obter versão do DeepEval
            mlflow.log_param("VECTOR_SEARCH_WEIGHT", settings.VECTOR_SEARCH_WEIGHT)
            # Adicionar outros parâmetros relevantes, ex: alpha, threshold, etc.
            # mlflow.log_param("alpha_hybrid_search", settings.VECTOR_SEARCH_WEIGHT) # Exemplo
            # mlflow.log_param("search_threshold", settings.SEARCH_THRESHOLD) # Exemplo
            logger.info("Parâmetros registrados no MLflow.")
        except Exception as e:
             logger.warning(f"Falha ao registrar parâmetros no MLflow: {e}")
        # -------------------------------------------

        # === 1. RAGAS Evaluation ===
        ragas_metrics = [
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        ]
        logger.info(f"Iniciando avaliação RAGAS com as métricas: {[m.name for m in ragas_metrics]}")
        ragas_evaluation_result = None
        try:
            ragas_evaluation_result = ragas_evaluate(
                ragas_dataset,
                metrics=ragas_metrics
            )
            logger.info("Avaliação RAGAS concluída.")
            print("\n--- Resultados da Avaliação RAGAS ---")
            print(ragas_evaluation_result.to_pandas())
            print("\n--- Scores Médios RAGAS ---")
            print(ragas_evaluation_result)
            print("---------------------------\n")

            # --- Registrar Métricas RAGAS no MLflow ---
            if ragas_evaluation_result:
                metric_keys_to_log = [
                    "faithfulness",
                    "answer_relevancy",
                    "context_precision",
                    "context_recall",
                ]
                logged_count = 0
                for metric_name in metric_keys_to_log:
                    try:
                        # Acessa a LISTA de scores para a métrica
                        scores_list = ragas_evaluation_result[metric_name]

                        # Verifica se é uma lista não vazia e calcula a média
                        if isinstance(scores_list, list) and scores_list:
                            # Tenta calcular a média (garantindo que sejam números)
                            numeric_scores = [s for s in scores_list if isinstance(s, (int, float))]
                            if numeric_scores:
                                average_score = sum(numeric_scores) / len(numeric_scores)
                                mlflow.log_metric(f"ragas_{metric_name}", average_score)
                                logged_count += 1
                            else:
                                logger.warning(f"Lista de scores para '{metric_name}' não contém valores numéricos.")
                        elif isinstance(scores_list, (int, float)):
                             # Caso raro onde ele retorna um único numero, loga diretamente
                             mlflow.log_metric(f"ragas_{metric_name}", scores_list)
                             logged_count += 1
                        else:
                            logger.warning(f"Não foi possível processar os scores para '{metric_name}' (tipo: {type(scores_list)}).")

                    except KeyError:
                         logger.warning(f"Métrica RAGAS '{metric_name}' não encontrada nos resultados.")
                    except Exception as e:
                         logger.error(f"Erro ao registrar métrica RAGAS '{metric_name}': {e}")

                if logged_count > 0:
                     logger.info(f"{logged_count} métricas RAGAS registradas no MLflow.")
                else:
                     logger.warning("Nenhuma métrica RAGAS foi registrada no MLflow.")
            # -----------------------------------------

        except Exception as e:
            logger.error(f"Erro durante a avaliação RAGAS: {e}", exc_info=True)
            print(f"\nErro durante a avaliação RAGAS: {e}")

        # === 2. DeepEval Evaluation ===
        logger.info("Preparando dados para DeepEval...")
        test_cases = []
        deepeval_metrics = []
        evaluation_result_obj = None # Renomeado para clareza
        try:
            for row in ragas_dataset:
                # Pula itens que tiveram erro na geração (opcional, mas recomendado)
                if row['answer'].startswith("ERRO:"):
                    logger.warning(f"Pulando item com erro anterior para DeepEval: {row['question'][:50]}...")
                    continue

                test_case = LLMTestCase(
                    input=row['question'],           # A pergunta original
                    actual_output=row['answer'],      # A resposta gerada pelo seu RAG
                    expected_output=row['ground_truth'], # A resposta ideal (usada por algumas métricas)
                    context=row['contexts']          # Os contextos recuperados (usado pela SummarizationMetric)
                    # retrieval_context=row['contexts'] # Poderia ser usado também se necessário
                )
                test_cases.append(test_case)

            if not test_cases:
                 logger.warning("Nenhum test case válido criado para DeepEval.")
            else:
                logger.info(f"Criados {len(test_cases)} test cases para DeepEval.")

                # --- Definir Critérios para GEval ---
                coherence_criteria = """
                Avalie a coerência da resposta ('actual_output').
                A resposta flui logicamente? As frases e parágrafos estão bem conectados?
                A estrutura geral da resposta faz sentido em relação à pergunta ('input')?
                Ignore pequenas imperfeições se a lógica geral for sólida.
                """

                linguistic_quality_criteria = """
                Avalie a qualidade linguística da resposta ('actual_output').
                A resposta está gramaticalmente correta? O vocabulário é apropriado e preciso?
                A resposta é clara, concisa e fácil de entender?
                Evite ser excessivamente crítico com pequenas falhas se a comunicação geral for eficaz.
                """
                # --- Fim Critérios para GEval ---

                # --- NOVO Critério para Diversidade/Concisão ---
                diversity_conciseness_criteria = """
                Avalie a diversidade e concisão da resposta ('actual_output').
                A resposta evita repetições desnecessárias de palavras, frases ou ideias?
                A resposta vai direto ao ponto, fornecendo a informação solicitada pela pergunta ('input') sem ser excessivamente verbosa ou prolixa?
                Uma resposta concisa e variada deve receber um score alto. Uma resposta repetitiva ou que adiciona informações não essenciais deve receber um score baixo.
                """
                # --- Fim NOVO Critério ---

                # Define as métricas DeepEval
                deepeval_metrics = [
                    BiasMetric(threshold=0.5),
                    ToxicityMetric(threshold=0.5),
                    GEval(
                        name="Coerência (GEval)",
                        criteria=coherence_criteria,
                        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
                        threshold=0.5
                    ),
                    GEval(
                        name="Qualidade Linguística (GEval)",
                        criteria=linguistic_quality_criteria,
                        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
                        threshold=0.5
                    ),
                    GEval(
                        name="Diversidade/Concisão (GEval)",
                        criteria=diversity_conciseness_criteria,
                        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
                        threshold=0.5
                    )
                ]
                logger.info(f"Iniciando avaliação DeepEval com as métricas: {[m.name if hasattr(m, 'name') else m.__class__.__name__ for m in deepeval_metrics]}")

                # --- Executa a avaliação e captura o objeto EvaluationResult ---
                evaluation_result_obj = deepeval_evaluate( # <<< Captura o objeto EvaluationResult
                    test_cases=test_cases,
                    metrics=deepeval_metrics,
                    print_results=False
                )
                logger.info("Avaliação DeepEval concluída.")

                # --- Calcular Médias e Registrar Métricas DeepEval no MLflow ---
                if evaluation_result_obj and hasattr(evaluation_result_obj, 'test_results'):
                    actual_test_results = evaluation_result_obj.test_results
                    if not actual_test_results:
                         logger.warning("O objeto EvaluationResult não contém resultados de testes ('test_results' está vazio).")

                    metric_scores = defaultdict(list)
                    metric_names = {}

                    for result in actual_test_results:
                         if not hasattr(result, 'metrics_data'):
                              logger.warning(f"Objeto TestResult não possui o atributo 'metrics_data'. Tipo: {type(result)}. Pulando.")
                              continue

                         for metric_metadata in result.metrics_data:
                            metric_internal_name = metric_metadata.name
                            # Tenta obter o nome 'bonito' (GEval)
                            original_metric = next((m for m in deepeval_metrics if (hasattr(m, 'name') and m.name == metric_internal_name) or m.__class__.__name__ == metric_internal_name), None)
                            log_name = metric_internal_name
                            if original_metric and hasattr(original_metric, 'name') and original_metric.name:
                                log_name = original_metric.name # Usa o nome que definimos, se houver

                            metric_names[metric_internal_name] = log_name # Guarda mapeamento

                            if isinstance(metric_metadata.score, (int, float)):
                                metric_scores[metric_internal_name].append(metric_metadata.score)

                    # Calcula e Loga as Médias
                    deepeval_logged_count = 0
                    for metric_internal_name, scores in metric_scores.items():
                        if scores:
                            average_score = sum(scores) / len(scores)
                            # Obtém o nome que queremos usar para log (pode ser o de GEval)
                            raw_log_metric_name = metric_names.get(metric_internal_name, metric_internal_name)
                            # Sanitiza o nome antes de logar <<< MUDANÇA AQUI
                            sanitized_log_metric_name = sanitize_mlflow_metric_name(raw_log_metric_name)

                            mlflow.log_metric(f"deepeval_{sanitized_log_metric_name}", average_score) # <<< Usa nome sanitizado
                            deepeval_logged_count += 1
                            # Log no console pode usar o nome original ou sanitizado
                            logger.info(f"Métrica DeepEval '{raw_log_metric_name}' (média): {average_score:.4f} -> Logged as 'deepeval_{sanitized_log_metric_name}'")

                    if deepeval_logged_count > 0:
                        logger.info(f"{deepeval_logged_count} métricas DeepEval (médias) registradas no MLflow.")
                    else:
                        logger.warning("Nenhuma métrica DeepEval com scores numéricos encontrada nos resultados para calcular médias.")

                elif evaluation_result_obj:
                     logger.warning("O objeto retornado por deepeval_evaluate não possui o atributo 'test_results'. Verifique a estrutura.")
                else:
                     logger.warning("A função deepeval_evaluate não retornou um objeto de resultado.")
            # ---------------------------------------------

        except Exception as e:
            # O erro INVALID_PARAMETER_VALUE acontecerá aqui se a sanitização falhar
            logger.error(f"Erro durante a avaliação DeepEval ou processamento/log: {e}", exc_info=True)
            print(f"\nErro durante a avaliação DeepEval ou processamento: {e}")
            print("Verifique a configuração da API Key (OpenAI) e se os modelos necessários estão acessíveis.")

        # --- Opcional: Registrar Dataset como Artefato ---
        # try:
        #     dataset_path = "/app/evaluation/datasets/sample_eval_set.py"
        #     if os.path.exists(dataset_path):
        #          mlflow.log_artifact(dataset_path, artifact_path="evaluation_dataset")
        #          logger.info(f"Dataset de avaliação registrado como artefato MLflow.")
        #     else:
        #          logger.warning(f"Arquivo do dataset não encontrado em {dataset_path} para registrar como artefato.")
        # except Exception as e:
        #      logger.warning(f"Falha ao registrar dataset como artefato MLflow: {e}")
        # -------------------------------------------------

        logger.info("Execução MLflow concluída.")


async def main():
    """
    Função principal para orquestrar a preparação dos dados e a avaliação.
    """
    logger.info("Obtendo configurações...")
    settings = None
    try:
        settings = get_settings() # Obter configurações
        # ----- Ponto Crítico de Refatoração -----
        # Substituir a chamada antiga por instanciação manual
        # rag_service_old = get_rag_service() # REMOVER
        rag_service = await manually_create_rag_service(settings) # Implementar esta função!
        # ---------------------------------------
        logger.info("RAGService instanciado manualmente.")
    except NotImplementedError as nie:
         logger.error(f"Erro: {nie}")
         print(f"ERRO: {nie}")
         return
    except Exception as e:
        logger.error(f"Falha ao inicializar o RAGService: {e}", exc_info=True)
        print(
            f"ERRO: Não foi possível inicializar o RAGService. Verifique as configurações e logs. Erro: {e}"
        )
        return

    prepared_dataset = await prepare_evaluation_data(rag_service)
    if prepared_dataset and settings: # Verifica se settings foi carregado
        await run_evaluation(prepared_dataset, settings) # Passar settings
    else:
        logger.error("Falha ao preparar os dados ou carregar configurações para avaliação.")


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
