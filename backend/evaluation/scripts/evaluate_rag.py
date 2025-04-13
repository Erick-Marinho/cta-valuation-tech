import asyncio
import logging
import os
import sys
import re
import importlib
from typing import Optional, List, Dict, Any

# --- SQLAlchemy/SQLModel Imports ---
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    AsyncEngine,
    async_sessionmaker,
)

# --- RAGAS Imports ---
from ragas import evaluate as ragas_evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from langchain_core.embeddings import Embeddings  # Para type hint

# --- DeepEval Imports ---
from deepeval import evaluate as deepeval_evaluate
from deepeval.metrics import BiasMetric, ToxicityMetric, GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

# --- MLflow Import ---
import mlflow

# --- Configuração do Logging PRIMEIRO ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
# --- Fim Configuração do Logging ---

# --- (Seção de Configuração do Caminho REMOVIDA) ---
# Assumimos que o PYTHONPATH ou WORKDIR no Docker permite encontrar 'backend'

logger.info(f"Python Executable: {sys.executable}")
logger.info(f"Initial sys.path: {sys.path}")
logger.info(f"Current Working Directory: {os.getcwd()}")

# --- Importações Essenciais (Configurações e Dados) ---
try:
    # Importa a função para obter configurações e a classe Settings
    from config.config import get_settings, Settings

    # Importa o dataset de avaliação
    from evaluation.datasets.sample_eval_set import evaluation_dataset

    # SQLAlchemy Async
    from sqlalchemy.ext.asyncio import (
        create_async_engine,
        AsyncSession,
        AsyncEngine,
        async_sessionmaker,
    )

    # RAGAS
    from ragas import evaluate as ragas_evaluate
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    )
    from langchain_core.embeddings import Embeddings  # Type hint para wrapper

    # DeepEval
    from deepeval import evaluate as deepeval_evaluate
    from deepeval.metrics import BiasMetric, ToxicityMetric, GEval
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams

    # MLflow
    import mlflow

    # Datasets (Hugging Face) - Importar aqui se ainda não foi importado
    from datasets import Dataset  # Garante que está importado

    # Implementações Concretas de Infraestrutura
    from infrastructure.external_services.embedding.huggingface_embedding_provider import (
        HuggingFaceEmbeddingProvider,
    )
    from infrastructure.llm.providers.nvidia_provider import NvidiaProvider
    from infrastructure.persistence.sqlmodel.repositories.sm_chunk_repository import (
        SqlModelChunkRepository,
    )
    from infrastructure.reranking.cross_encoder_reranker import CrossEncoderReRanker

    # Classe do Serviço de Aplicação
    # from application.services.rag_service import RAGService
    # Importar o Caso de Uso
    from application.use_cases.rag.process_query_use_case import ProcessQueryUseCase

    # Wrapper Langchain (para RAGAS)
    from infrastructure.embedding.langchain_wrappers import (
        LangChainHuggingFaceEmbeddings,
    )

    # Utilitários (se necessário mais tarde)
    from collections import defaultdict  # Para agregação de scores DeepEval
    import pandas as pd  # Para checar NaN e talvez mostrar resultados RAGAS

    logger.info(
        "Todas as importações essenciais e de infra/avaliação realizadas com sucesso."
    )

except ImportError as e:
    # Log detalhado se a importação falhar
    logger.error(f"Erro fatal ao importar configurações ou dataset: {e}", exc_info=True)
    logger.error(
        "Verifique se o PYTHONPATH está configurado corretamente no ambiente (Docker) e se os arquivos/pacotes existem."
    )
    sys.exit(1)
except Exception as e:
    # Captura outros erros inesperados durante a importação
    logger.error(f"Erro inesperado durante importações essenciais: {e}", exc_info=True)
    sys.exit(1)
# --- Fim Importações Essenciais ---


# --- Funções Auxiliares (mantidas) ---
def sanitize_mlflow_metric_name(name: str) -> str:
    """Substitui caracteres inválidos para nomes de métricas MLflow."""
    name = re.sub(r"[ ()/<>,.]", "_", name)  # Substitui mais caracteres problemáticos
    name = re.sub(r"[^a-zA-Z0-9_/-]", "", name)  # Permite letras, números, _, /, -
    name = re.sub(r"_+", "_", name)
    name = name.strip("_")
    return name if name else "invalid_metric_name"


def get_library_version(library_name: str) -> str:
    """Tenta obter a versão de uma biblioteca instalada."""
    try:
        lib = importlib.import_module(library_name)
        return getattr(lib, "__version__", "unknown")
    except ImportError:
        return "not_found"
    except Exception:
        return "error_getting_version"


# --- Implementação de prepare_evaluation_data ---
async def prepare_evaluation_data(process_query_uc: ProcessQueryUseCase) -> Dataset:
    """
    Prepara os dados para avaliação chamando o ProcessQueryUseCase para cada pergunta
    no dataset de avaliação e coletando os resultados.
    """
    processed_data = []
    total_items = len(evaluation_dataset)
    logger.info(
        f"Iniciando preparação de dados para {total_items} itens do dataset de avaliação."
    )

    for i, item in enumerate(evaluation_dataset):
        question = item.get("question", "")
        ground_truth_answer = item.get("ground_truth_answer", "")  # Resposta ideal
        ground_truth_contexts = item.get(
            "ground_truths", []
        )  # Contextos ideais (List[str])

        if not question:
            logger.warning(f"Item {i+1} pulado: 'question' está vazio.")
            continue

        logger.info(f"Processando item {i+1}/{total_items}: '{question[:60]}...'")

        answer = "ERRO: Falha na execução do ProcessQueryUseCase"
        contexts = []

        try:
            start_query_time = asyncio.get_event_loop().time()
            result = await process_query_uc.execute(
                query=question, include_debug_info=True
            )
            query_duration = asyncio.get_event_loop().time() - start_query_time
            logger.info(f"Item {i+1} processado pelo ProcessQueryUseCase em {query_duration:.2f}s.")

            answer = result.get("response", "")
            debug_info = result.get("debug_info", {})

            # --- EXTRAÇÃO DE CONTEXTO (SIMPLIFICADA) ---
            final_chunk_details = debug_info.get("final_chunk_details", [])
            placeholders_used = False

            # Tentar obter o texto diretamente de 'text_content' em final_chunk_details
            if (final_chunk_details and
                isinstance(final_chunk_details, list) and
                len(final_chunk_details) > 0 and
                isinstance(final_chunk_details[0], dict) and
                "text_content" in final_chunk_details[0]):

                contexts = [details.get("text_content", "") for details in final_chunk_details]
                logger.debug(f"Contextos obtidos diretamente de 'text_content' para item {i+1}.")
                # Verificar se algum contexto ainda está vazio (improvável, mas possível)
                if not all(contexts):
                    logger.warning(f"Alguns contextos extraídos de 'text_content' estão vazios para item {i+1}.")

            else:
                # Se 'text_content' não estiver disponível ou a estrutura for inesperada, logar e usar placeholders
                logger.warning(
                    f"Não foi possível extrair 'text_content' de final_chunk_details para item {i+1} ('{question[:30]}...'). Verifique o debug_info do ProcessQueryUseCase. Usando placeholders."
                )
                # Criar placeholders baseados no número de chunks reportados (se disponível)
                num_results = debug_info.get("num_results", len(final_chunk_details))
                contexts = [f"Placeholder Context {j+1} (text missing)" for j in range(num_results)]
                placeholders_used = True

            # --- FIM DA EXTRAÇÃO DE CONTEXTO (SIMPLIFICADA) ---

            if not answer:
                logger.warning(f"Resposta gerada vazia para item {i+1}.")
            if not contexts or placeholders_used:
                 if placeholders_used:
                      logger.warning(f"Contextos para item {i+1} são placeholders. Métricas de contexto RAGAS podem ser 0 ou imprecisas.")
                 else: # contexts is empty list
                      logger.warning(f"Nenhum contexto recuperado/processado para item {i+1}.")

            if not ground_truth_contexts:
                logger.warning(
                    f"Item {i+1} não possui 'ground_truths' (contextos ideais). Context Recall será 0."
                )

        except Exception as e:
            logger.error(f"Erro ao processar item {i+1} ('{question[:60]}...') com ProcessQueryUseCase: {e}", exc_info=True)
            answer = f"ERRO: {type(e).__name__}"
            contexts = []

        # Adiciona o ponto de dados para o dataset RAGAS/DeepEval
        processed_data.append(
            {
                "question": question,
                "answer": answer,
                "contexts": contexts, # Lista simplificada
                "ground_truth": ground_truth_answer,
                "ground_truths": ground_truth_contexts,
            }
        )

    logger.info(
        f"Preparação de dados concluída. {len(processed_data)} pontos de dados processados."
    )

    if not processed_data:
        logger.warning(
            "Nenhum dado foi processado com sucesso. Retornando dataset vazio."
        )
        return Dataset.from_list([])

    # Converte a lista de dicionários para o formato Dataset do Hugging Face
    try:
        evaluation_hf_dataset = Dataset.from_list(processed_data)
        logger.info("Dataset Hugging Face criado com sucesso.")
        return evaluation_hf_dataset
    except Exception as e:
        logger.error(
            f"Erro ao converter dados processados para Dataset Hugging Face: {e}",
            exc_info=True,
        )
        # Retorna um dataset vazio em caso de erro na conversão
        return Dataset.from_list([])


# --- Implementação de run_evaluation ---
async def run_evaluation(
    ragas_dataset: Dataset, settings: Settings, embedding_model_wrapper: Embeddings
):
    """
    Executa as avaliações RAGAS e DeepEval usando o dataset preparado,
    logando parâmetros e métricas no MLflow.
    """
    logger.info("Iniciando a fase de avaliação RAGAS e DeepEval...")

    # --- Configuração e Início da Run MLflow ---
    # Lê URI do env var ou das settings, com fallback para diretório local
    mlflow_uri = os.getenv(
        "MLFLOW_TRACKING_URI", settings.MLFLOW_TRACKING_URI or "./mlruns"
    )
    mlflow.set_tracking_uri(mlflow_uri)
    logger.info(f"MLflow Tracking URI configurado para: {mlflow_uri}")

    try:
        # Inicia uma nova run no MLflow
        with mlflow.start_run() as run:
            run_id = run.info.run_id
            logger.info(f"Execução MLflow iniciada. Run ID: {run_id}")
            print(f"\n--- Iniciando MLflow Run: {run_id} ---")
            print(f"MLflow UI: {mlflow_uri}")  # Mostra onde ver a UI

            # --- 1. Log Parâmetros do Experimento ---
            logger.info("Registrando parâmetros do experimento no MLflow...")
            try:
                params_to_log = {
                    "llm_model_rag": settings.LLM_MODEL,
                    "embedding_model_rag": settings.EMBEDDING_MODEL,
                    "vector_search_weight": settings.VECTOR_SEARCH_WEIGHT,
                    "reranker_model": settings.RERANKER_MODEL,
                    "chunk_size": settings.CHUNK_SIZE,
                    "chunk_overlap": settings.CHUNK_OVERLAP,
                    "top_k_retriever": "N/A (ver ProcessQueryUseCase)",
                    "dataset_size": len(ragas_dataset),
                    "deepeval_version": get_library_version("deepeval"),
                    "ragas_version": get_library_version("ragas"),
                    "evaluation_llm_provider": "OpenAI (via OPENAI_API_KEY)",
                }
                mlflow.log_params(params_to_log)
                logger.info(f"{len(params_to_log)} parâmetros registrados no MLflow.")
            except Exception as e:
                logger.warning(
                    f"Falha ao registrar parâmetros no MLflow: {e}", exc_info=True
                )

            # --- 2. Executar Avaliação RAGAS ---
            logger.info("Iniciando avaliação RAGAS...")
            ragas_metrics_to_run = [
                faithfulness,  # Usa LLM (OpenAI default)
                answer_relevancy,  # Usa LLM e Embedding (OpenAI default + nosso)
                context_precision,  # Usa LLM (OpenAI default)
                context_recall,  # Usa LLM e Embedding (OpenAI default + nosso)
            ]
            logger.info(
                f"Métricas RAGAS a serem executadas: {[m.name for m in ragas_metrics_to_run]}"
            )

            ragas_result = None
            try:
                # Executa RAGAS, passando o dataset e o wrapper de embedding.
                # O LLM usado será o padrão (OpenAI) via API Key do ambiente.
                ragas_result = await asyncio.to_thread(  # Executa ragas_evaluate em thread separada
                    ragas_evaluate,
                    dataset=ragas_dataset,
                    metrics=ragas_metrics_to_run,
                    embeddings=embedding_model_wrapper,
                )
                logger.info("Avaliação RAGAS concluída.")
                # Opcional: Mostrar resultados no console
                print("\n--- Scores Médios RAGAS ---")
                print(ragas_result)
                print("---------------------------\n")

                # Após executar ragas_evaluate e receber o resultado
                if ragas_result:
                    # Primeiro, tente extrair as métricas usando os métodos da API
                    try:
                        # Converter para DataFrame para visualização
                        ragas_df = ragas_result.to_pandas()
                        print("\n--- Scores RAGAS Detalhados ---")
                        print(ragas_df)
                        print("-------------------------------\n")
                        
                        # Extrair média de cada métrica para logging no MLflow
                        metric_means = {}
                        for metric in ragas_metrics_to_run:
                            metric_name = metric.name
                            # Verificar se a métrica está no DataFrame
                            if metric_name in ragas_df.columns:
                                # Calcular média, ignorando NaN
                                mean_value = ragas_df[metric_name].mean()
                                metric_means[metric_name] = mean_value
                        
                        # Log para MLflow
                        for metric_name, mean_value in metric_means.items():
                            if not pd.isna(mean_value):  # Verificar se não é NaN
                                mlflow.log_metric(f"ragas_{metric_name}", mean_value)
                                print(f"Logged {metric_name}: {mean_value}")
                    
                    except Exception as e:
                        logger.error(f"Erro ao processar resultados RAGAS: {e}", exc_info=True)

            except Exception as e:
                logger.error(
                    f"Erro crítico durante a avaliação RAGAS: {e}", exc_info=True
                )
                # Logar falha no MLflow, se possível
                try:
                    mlflow.log_param("ragas_evaluation_status", "failed")
                except:
                    pass  # Ignora erro se o log falhar

            # --- 3. Executar Avaliação DeepEval ---
            logger.info("Preparando dados e iniciando avaliação DeepEval...")
            test_cases = []
            # Prepara os test cases a partir do dataset RAGAS
            for i, row in enumerate(ragas_dataset):
                # Pula itens que já tiveram erro na geração da resposta
                if isinstance(row.get("answer"), str) and row["answer"].startswith(
                    "ERRO:"
                ):
                    logger.warning(
                        f"Pulando item {i+1} com erro anterior para DeepEval: {row.get('question', 'N/A')[:50]}..."
                    )
                    continue
                # Garante que context seja List[str]
                context_list = row.get("contexts", [])
                if not isinstance(context_list, list):
                    context_list = [str(context_list)]
                if context_list and not isinstance(context_list[0], str):
                    context_list = [str(c) for c in context_list]

                test_cases.append(
                    LLMTestCase(
                        input=row.get("question", ""),
                        actual_output=row.get("answer", ""),
                        expected_output=row.get("ground_truth"),  # Pode ser None
                        context=context_list,
                        retrieval_context=context_list,  # Usado por algumas métricas de contexto
                    )
                )

            if not test_cases:
                logger.warning(
                    "Nenhum test case válido criado para DeepEval. Avaliação pulada."
                )
            else:
                logger.info(f"Criados {len(test_cases)} test cases para DeepEval.")

                # Define as métricas DeepEval
                # ATENÇÃO: Alterado 'gpt-4' para 'gpt-4-turbo'
                deepeval_metrics = [
                    BiasMetric(threshold=0.5, model="gpt-4-turbo", strict_mode=False),
                    ToxicityMetric(threshold=0.5, model="gpt-4-turbo", strict_mode=False),
                    GEval(
                        name="Coerência",
                        criteria="Avalie a coerência da resposta ('actual_output') em relação à pergunta ('input').",
                        evaluation_params=[
                            LLMTestCaseParams.INPUT,
                            LLMTestCaseParams.ACTUAL_OUTPUT,
                        ],
                        model="gpt-4-turbo",
                        threshold=0.5,
                    ),
                    GEval(
                        name="Qualidade_Linguística",
                        criteria="Avalie a qualidade linguística (gramática, clareza, concisão) da resposta ('actual_output').",
                        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
                        model="gpt-4-turbo",
                        threshold=0.5,
                    ),
                    GEval(
                        name="Relevância_Contextual",
                        criteria="Avalie se a resposta ('actual_output') é relevante e baseada nos contextos ('context') fornecidos.",
                        evaluation_params=[
                            LLMTestCaseParams.ACTUAL_OUTPUT,
                            LLMTestCaseParams.CONTEXT,
                        ],
                        model="gpt-4-turbo",
                        threshold=0.5,
                    ),
                ]
                logger.info(
                    f"Métricas DeepEval a serem executadas: {[m.name if hasattr(m, 'name') else m.__class__.__name__ for m in deepeval_metrics]}"
                )

                deepeval_result = None
                try:
                    # Executa DeepEval. Pode demorar e fazer várias chamadas à API OpenAI.
                    # ATENÇÃO: Requer OPENAI_API_KEY configurada no ambiente!
                    deepeval_result = await asyncio.to_thread(  # Executa deepeval_evaluate em thread separada
                        deepeval_evaluate,
                        test_cases=test_cases,
                        metrics=deepeval_metrics,
                        print_results=False,  # Evita print massivo
                    )
                    logger.info("Avaliação DeepEval concluída.")

                    # Log DeepEval metrics to MLflow
                    if deepeval_result:
                        logger.info(f"Tipo do objeto DeepEval: {type(deepeval_result)}")
                        deepeval_logged_count = 0
                        
                        # Baseado na implementação anterior que funcionava
                        if hasattr(deepeval_result, 'test_results'):
                            actual_test_results = deepeval_result.test_results
                            if actual_test_results:
                                metric_scores = defaultdict(list)
                                metric_names = {}

                                for result in actual_test_results:
                                    if hasattr(result, 'metrics_data'):
                                        for metric_metadata in result.metrics_data:
                                            metric_internal_name = metric_metadata.name
                                            # Registra o nome para uso posterior
                                            metric_names[metric_internal_name] = metric_internal_name

                                            # Coleta o score se for numérico
                                            if hasattr(metric_metadata, 'score') and isinstance(metric_metadata.score, (int, float)):
                                                metric_scores[metric_internal_name].append(metric_metadata.score)

                                # Calcula e registra as médias no MLflow
                                for metric_internal_name, scores in metric_scores.items():
                                    if scores:
                                        average_score = sum(scores) / len(scores)
                                        sanitized_name = sanitize_mlflow_metric_name(f"deepeval_{metric_internal_name}")
                                        mlflow.log_metric(sanitized_name, average_score)
                                        deepeval_logged_count += 1
                                        logger.info(f"Métrica DeepEval '{metric_internal_name}': {average_score:.4f}")
                                
                                if deepeval_logged_count > 0:
                                    logger.info(f"{deepeval_logged_count} métricas DeepEval registradas com sucesso no MLflow.")
                                else:
                                    logger.warning("Nenhuma métrica com scores numéricos encontrada nos resultados DeepEval.")
                            else:
                                logger.warning("O objeto DeepEval contém 'test_results', mas está vazio.")
                        else:
                            # Segunda tentativa: verificar se há métricas diretamente no objeto de resultado
                            metrics_found = False
                            
                            # Tenta acessar estruturas alternativas que podem existir na versão 2.6.6
                            try:
                                # Exibe todos os atributos disponíveis para debug
                                logger.info(f"Atributos do objeto DeepEval: {dir(deepeval_result)}")
                                
                                # Verifica se o objeto tem um atributo que contém as métricas
                                for attr_name in ['metrics', 'results', 'test_cases', 'evaluation_results']:
                                    if hasattr(deepeval_result, attr_name):
                                        attr_value = getattr(deepeval_result, attr_name)
                                        logger.info(f"Encontrado atributo '{attr_name}': {type(attr_value)}")
                                        metrics_found = True
                                        
                                        # Tenta processar este atributo se for uma coleção
                                        if isinstance(attr_value, (list, tuple)) and attr_value:
                                            for item in attr_value:
                                                # Log para debug
                                                logger.info(f"Item em '{attr_name}': {type(item)}")
                                                
                                                # Tenta extrair métricas deste item
                                                if hasattr(item, 'score') and isinstance(item.score, (int, float)):
                                                    name = getattr(item, 'name', attr_name)
                                                    sanitized_name = sanitize_mlflow_metric_name(f"deepeval_{name}")
                                                    mlflow.log_metric(sanitized_name, item.score)
                                                    deepeval_logged_count += 1
                                                    logger.info(f"Métrica DeepEval '{name}': {item.score:.4f}")
                                
                                if not metrics_found:
                                    logger.warning("Não foi possível encontrar estruturas de métricas conhecidas no objeto DeepEval.")
                            except Exception as e:
                                logger.error(f"Erro ao tentar extrações alternativas: {e}")
                            
                            # Se chegamos aqui sem encontrar métricas, exibimos um aviso final
                            if deepeval_logged_count == 0:
                                logger.warning("Nenhuma métrica DeepEval processada com sucesso para registro no MLflow.")

                except Exception as e:
                    # Captura erros como RateLimitError da OpenAI, etc.
                    logger.error(
                        f"Erro crítico durante a avaliação DeepEval: {e}", exc_info=True
                    )
                    # Logar falha no MLflow
                    try:
                        mlflow.log_param("deepeval_evaluation_status", "failed")
                    except:
                        pass  # Ignora erro no log

            # --- Fim da Run MLflow ---
            logger.info(f"Finalizando MLflow Run: {run_id}")
            print(f"--- MLflow Run {run_id} Concluída ---")

    except Exception as mlflow_exc:
        # Captura erro ao iniciar a run do MLflow (ex: URI inválido)
        logger.error(
            f"Erro ao configurar ou iniciar a run do MLflow: {mlflow_exc}",
            exc_info=True,
        )
        print(
            f"\nERRO: Falha ao iniciar ou executar a run do MLflow. Verifique a configuração do MLFLOW_TRACKING_URI ({mlflow_uri})."
        )


# --- Função Principal (main) ---
async def main():
    """Função principal para orquestrar a avaliação."""
    logger.info("Iniciando a execução do script de avaliação RAG (modo Docker)...")
    settings: Optional[Settings] = None
    engine: Optional[AsyncEngine] = None
    embedding_provider: Optional[HuggingFaceEmbeddingProvider] = None
    llm_provider: Optional[NvidiaProvider] = None
    reranker: Optional[CrossEncoderReRanker] = None
    langchain_embedding_wrapper: Optional[LangChainHuggingFaceEmbeddings] = None
    async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None
    process_query_uc: Optional[ProcessQueryUseCase] = None

    try:
        # 1. Carregar Configurações
        settings = get_settings()
        logger.info("Configurações carregadas.")
        
        # Configurar OpenAI API Key do settings para as bibliotecas de avaliação
        if settings.OPENAI_API_KEY:
            # Para RAGAS e outras bibliotecas que usam OpenAI
            os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
            logger.info("OPENAI_API_KEY configurada a partir do settings (.env)")
        else:
            logger.warning("OPENAI_API_KEY não encontrada no settings (.env). Dependendo de variáveis de ambiente.")
        
        logger.info(f"Dataset carregado ({len(evaluation_dataset)} itens).")

        # 2. Criar Engine SQLAlchemy Async
        if not settings.DATABASE_URL:
            raise ValueError("DATABASE_URL não configurada.")
        logger.info(f"Criando engine SQLAlchemy...")
        try:
            engine = create_async_engine(
                settings.DATABASE_URL, echo=False, pool_pre_ping=True
            )
        except Exception as db_exc:
            raise RuntimeError(f"Falha ao criar AsyncEngine: {db_exc}") from db_exc
        logger.info("AsyncEngine criado.")

        # 3. Instanciar Provedores
        logger.info("Instanciando provedores...")
        try:
            embedding_provider = HuggingFaceEmbeddingProvider()
            llm_provider = NvidiaProvider()
            reranker = CrossEncoderReRanker()
        except Exception as provider_exc:
            raise RuntimeError(
                f"Falha ao instanciar provedores: {provider_exc}"
            ) from provider_exc
        logger.info("Provedores instanciados.")

        # 4. Criar Wrapper Langchain Embedding
        if not embedding_provider:
            raise ValueError("Embedding Provider não instanciado.")
        logger.info("Criando wrapper Langchain Embedding...")
        try:
            langchain_embedding_wrapper = LangChainHuggingFaceEmbeddings(
                provider=embedding_provider
            )
        except Exception as wrapper_exc:
            raise RuntimeError(
                f"Falha ao criar wrapper Langchain Embedding: {wrapper_exc}"
            ) from wrapper_exc
        logger.info("Wrapper Langchain Embedding criado.")

        # 5. Criar Session Factory
        if not engine:
            raise ValueError("Engine não criado.")
        logger.info("Criando fábrica de sessões SQLAlchemy...")
        try:
            async_session_factory = async_sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )
        except Exception as factory_exc:
            raise RuntimeError(
                f"Falha ao criar fábrica de sessões: {factory_exc}"
            ) from factory_exc
        logger.info("Fábrica de sessões criada.")

        # --- Lógica Principal com Sessão ---
        if not async_session_factory:
            raise ValueError("Fábrica de sessões não criada.")
        if not all(
            [embedding_provider, llm_provider, reranker, langchain_embedding_wrapper]
        ):
            raise ValueError("Componentes não instanciados.")

        logger.info("Iniciando contexto de sessão para avaliação...")
        async with async_session_factory() as session:
            logger.info("Sessão async iniciada.")

            # 7. Instanciar Repositório
            logger.info("Instanciando repositório Chunk...")
            try:
                chunk_repo = SqlModelChunkRepository(session=session)
            except Exception as repo_exc:
                raise RuntimeError(
                    f"Falha ao instanciar repositório Chunk: {repo_exc}"
                ) from repo_exc
            logger.info("Repositório Chunk instanciado.")

            # 8. Instanciar ProcessQueryUseCase em vez de RAGService
            logger.info("Instanciando ProcessQueryUseCase...")
            try:
                if not all([embedding_provider, llm_provider, chunk_repo, reranker]):
                    raise ValueError("Dependência nula.")
                process_query_uc = ProcessQueryUseCase(
                    embedding_provider=embedding_provider,
                    llm_provider=llm_provider,
                    chunk_repository=chunk_repo,
                    reranker=reranker,
                )
            except Exception as uc_exc:
                raise RuntimeError(
                    f"Falha ao instanciar ProcessQueryUseCase: {uc_exc}"
                ) from uc_exc
            logger.info("ProcessQueryUseCase instanciado.")

            # 9. Preparar Dados (Passar o Use Case)
            logger.info("Preparando dados para avaliação...")
            if not process_query_uc:
                 raise ValueError("ProcessQueryUseCase não foi instanciado.")
            prepared_hf_dataset = await prepare_evaluation_data(process_query_uc)

            # 10. Executar Avaliação
            if prepared_hf_dataset and len(prepared_hf_dataset) > 0:
                logger.info(
                    f"Iniciando a execução da avaliação com {len(prepared_hf_dataset)} pontos de dados..."
                )
                await run_evaluation(
                    prepared_hf_dataset, settings, langchain_embedding_wrapper
                )
            else:
                logger.error(
                    "Dataset preparado vazio ou com falha na criação. Nenhuma avaliação será executada."
                )

            logger.info("Saindo do contexto da sessão.")
        logger.info("Contexto de sessão finalizado.")

    except Exception as e:
        logger.error(f"Erro durante a execução do script: {e}", exc_info=True)

    finally:
        # 11. Limpar Engine
        if engine:
            logger.info("Finalizando engine SQLAlchemy...")
            try:
                await engine.dispose()
            except Exception as dispose_exc:
                logger.error(f"Erro ao finalizar engine: {dispose_exc}", exc_info=True)
            logger.info("Engine finalizado.")
        else:
            logger.info("Nenhum engine SQLAlchemy para finalizar.")

        logger.info("Script de avaliação finalizado.")


# --- Ponto de Entrada do Script (sem mudanças) ---
if __name__ == "__main__":
    logger.info(f"Executando script diretamente: {__file__}")
    try:
        # Ajustado para chamar a função main atualizada
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Execução interrompida pelo usuário.")
    except Exception as e:
        logger.critical(
            f"Erro fatal não tratado na execução principal: {e}", exc_info=True
        )
        sys.exit(1)
