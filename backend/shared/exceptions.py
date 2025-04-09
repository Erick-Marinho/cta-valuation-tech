"""
Exceções específicas da lógica de negócio.
"""


class CoreException(Exception):
    """Exceção base para erros na camada de negócio."""

    pass


class DocumentProcessingError(CoreException):
    """Erro ao processar um documento."""

    pass


class EmbeddingError(CoreException):
    """Erro ao gerar embeddings."""

    pass


class RAGProcessingError(CoreException):
    """Erro ao processar consulta RAG."""

    pass


class LLMServiceError(CoreException):
    """Erro no serviço de LLM."""

    pass


class ConfigurationError(CoreException):
    """Erro de configuração."""

    pass


class ValidationError(CoreException):
    """Erro de validação de dados."""

    pass


class ServiceUnavailableError(CoreException):
    """Serviço temporariamente indisponível."""

    pass


class ResourceNotFoundError(CoreException):
    """Recurso não encontrado."""

    pass
