from dataclasses import dataclass
from typing import List

@dataclass(frozen=True) # Value Objects são imutáveis
class Embedding:
    """
    Representa um vetor de embedding como um Value Object.

    Atributos:
        vector (List[float]): O vetor numérico do embedding.
    """
    vector: List[float]

    def __post_init__(self):
        # Validação opcional: garantir que o vetor não está vazio,
        # ou tem uma dimensão específica, se necessário.
        if not self.vector:
            raise ValueError("O vetor de embedding não pode estar vazio.")
        # Exemplo: if len(self.vector) != 768:
        #     raise ValueError("Dimensão do embedding inválida.")

    def as_list(self) -> List[float]:
        """Retorna o vetor como uma lista padrão."""
        return self.vector

    # Poderíamos adicionar outros métodos úteis aqui no futuro,
    # como cálculo de similaridade (embora isso possa pertencer a um serviço).
