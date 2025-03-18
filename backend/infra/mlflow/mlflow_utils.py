import mlflow
import os
import time
from datetime import datetime
from functools import wraps
import json

class RAGExperimentTracker:
    def __init__(self, experiment_name="rag_pipeline"):
        # Configurar caminho do MLflow - solução para Windows
        mlflow_dir = os.path.join(os.getcwd(), "mlruns")
        if not os.path.exists(mlflow_dir):
            os.makedirs(mlflow_dir)
            
        # No Windows, usar caminho direto em vez de file://
        # Isso resolve o erro de URI
        mlflow.set_tracking_uri(None)  # Usar diretório padrão './mlruns'
        
        # Configurar ou carregar experimento
        try:
            self.experiment_id = mlflow.create_experiment(experiment_name)
        except:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            self.experiment_id = experiment.experiment_id if experiment else None

    def log_document_processing(self, func):
        """Decorator para rastrear processamento de documentos"""
        @wraps(func)
        async def wrapper(document_service, file_name, file_content, file_type, metadata=None):
            start_time = time.time()
            
            with mlflow.start_run(experiment_id=self.experiment_id, 
                                run_name=f"document_processing_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
                # Log parâmetros
                mlflow.log_param("file_name", file_name)
                mlflow.log_param("file_type", file_type)
                mlflow.log_param("file_size_kb", len(file_content) / 1024)
                
                # Processar documento
                document = await func(document_service, file_name, file_content, file_type, metadata)
                
                # Log métricas
                processing_time = time.time() - start_time
                mlflow.log_metric("processing_time_seconds", processing_time)
                mlflow.log_metric("chunks_count", document.chunks_count)
                
                # Log metadados adicionais
                if hasattr(document, "embedding_model"):
                    mlflow.log_param("embedding_model", document.embedding_model)
                
                # Salvando arquivo JSON com os chunks (se disponível)
                if hasattr(document, "chunks") and document.chunks:
                    import json
                    chunks_file = f"chunks_outputs/{file_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    with open(chunks_file, "w", encoding="utf-8") as f:
                        json.dump([{str(i+1): chunk} for i, chunk in enumerate(document.chunks)], 
                                f, ensure_ascii=False, indent=4)
                    mlflow.log_artifact(chunks_file)
                
                return document
        
        return wrapper

    def log_query_processing(self, func):
        """Decorator para rastrear processamento de consultas"""
        @wraps(func)
        async def wrapper(rag_service, query, *args, **kwargs):
            start_time = time.time()
            
            with mlflow.start_run(experiment_id=self.experiment_id, 
                                run_name=f"query_processing_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
                # Log parâmetros
                mlflow.log_param("query", query)
                mlflow.log_param("query_length", len(query))
                
                # Processar consulta
                result = await func(rag_service, query, *args, **kwargs)
                
                # Log métricas
                processing_time = time.time() - start_time
                mlflow.log_metric("processing_time_seconds", processing_time)
                
                # Log métricas da busca se disponíveis
                if "debug_info" in result:
                    debug = result["debug_info"]
                    if "num_results" in debug:
                        mlflow.log_metric("num_results", debug["num_results"])
                    if "scores" in debug:
                        mlflow.log_metric("max_score", max(debug["scores"]) if debug["scores"] else 0)
                        mlflow.log_metric("min_score", min(debug["scores"]) if debug["scores"] else 0)
                        mlflow.log_metric("avg_score", sum(debug["scores"])/len(debug["scores"]) if debug["scores"] else 0)
                
                return result
        
        return wrapper

# Instância global para uso em toda a aplicação
experiment_tracker = RAGExperimentTracker() 