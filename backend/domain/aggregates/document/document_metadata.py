from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List

@dataclass(frozen=True) # Value Objects são imutáveis
class DocumentMetadata:
    """
    Value Object representando os metadados associados a um Documento.

    Inclui metadados extraídos do arquivo e metadados gerados
    durante o processamento.
    """
    # Metadados Extrínsecos (fornecidos ou extraídos do arquivo)
    source_filename: Optional[str] = None # Nome original pode ser útil
    page_count: Optional[int] = None
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: Optional[str] = None # Ou List[str]?
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[str] = None # Manter como string por simplicidade? Ou datetime?
    modification_date: Optional[str] = None

    # Metadados Intrínsecos (gerados/calculados)
    content_hash_sha256: Optional[str] = None
    extraction_status: Optional[str] = field(default="pending") # Ex: pending, success, failed
    chunking_strategy: Optional[str] = None # Ex: sentence, recursive

    # Campo genérico para metadados adicionais não mapeados
    # Usar com cautela para não virar um saco de gatos
    additional_properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """ Converte o VO para um dicionário, útil para serialização. """
        # asdict lida bem com dataclasses, mas podemos personalizar se necessário
        # (ex: filtrar Nones, formatar datas)
        data = asdict(self)
        # Opcional: Remover chaves com valor None
        # return {k: v for k, v in data.items() if v is not None}
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentMetadata':
        """ Cria uma instância do VO a partir de um dicionário. """
        # Precisamos lidar com campos que não existem no init
        known_field_names = {f.name for f in cls.__dataclass_fields__.values()}
        init_data = {k: v for k, v in data.items() if k in known_field_names and k != 'additional_properties'}
        additional_props = {k: v for k, v in data.items() if k not in known_field_names}

        # Passa os dados conhecidos para o construtor
        instance = cls(**init_data)

        # Atribui as propriedades adicionais (dataclass(frozen=True) impede isso diretamente)
        # Precisamos de um truque ou remover frozen=True se 'additional_properties' for essencial
        # Solução alternativa: recriar o objeto se additional_properties for necessário
        if additional_props:
             # Isso recria o objeto, perdendo a imutabilidade estrita no processo de criação
             # mas o objeto final ainda será "imutável" (sem métodos de alteração)
             final_data = init_data
             final_data['additional_properties'] = additional_props
             return cls(**final_data)

        return instance
