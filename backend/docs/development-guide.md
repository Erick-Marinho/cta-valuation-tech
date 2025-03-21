# Guia de Desenvolvimento

Este guia fornece informações detalhadas para desenvolvedores que desejam contribuir ou modificar a API CTA Value Tech.

## Arquitetura do Projeto

A API segue uma arquitetura em camadas com separação clara de responsabilidades:

```
backend/
├── api/                  # Camada de API (endpoints)
│   ├── endpoints/        # Definições de endpoints por recurso
│   └── dependencies.py   # Dependências compartilhadas
├── core/                 # Lógica de negócio central
│   ├── models/           # Modelos de domínio
│   ├── services/         # Serviços de negócio
│   └── exceptions.py     # Exceções de negócio
├── db/                   # Acesso a dados
│   ├── models/           # Modelos de banco de dados
│   ├── repositories/     # Repositórios por entidade
│   └── connection.py     # Gerenciamento de conexões
├── infra/                # Adaptadores para serviços externos
│   ├── embedding/        # Adaptadores para embeddings
│   ├── llm/              # Adaptadores para LLMs
│   └── storage/          # Adaptadores para armazenamento
├── processors/           # Processamento de dados e textos
│   ├── chunkers/         # Divisão de textos em chunks
│   ├── extractors/       # Extração de texto de documentos
│   └── normalizers/      # Normalização e limpeza de textos
├── utils/                # Utilitários compartilhados
├── app.py                # Ponto de entrada da aplicação
└── config.py             # Configurações centralizadas
```

## Fluxo de Dados Principal

1. **Upload de Documento**:
   - O documento é enviado via API
   - O serviço de documentos processa o arquivo
   - O texto é extraído e dividido em chunks
   - Embeddings são gerados para cada chunk
   - Os chunks e embeddings são armazenados no banco de dados

2. **Consulta RAG**:
   - O usuário envia uma consulta
   - A consulta é processada e transformada em embedding
   - O sistema busca chunks similares no banco de dados
   - Os chunks relevantes são selecionados e reordenados
   - O contexto é montado e enviado ao LLM
   - A resposta gerada é retornada ao usuário

## Padrões de Código

### Injeção de Dependência

Utilizamos o sistema de dependências do FastAPI para injeção. Exemplo:

```python
@router.get("/", response_model=HealthResponse)
async def health_check(
    settings: Settings = Depends(get_settings),
    embedding_service: EmbeddingService = Depends(get_embedding_service)
):
    # Implementação...
```

### Padrão Repositório

Isolamos o acesso ao banco de dados em repositórios especializados:

```python
class DocumentoRepository:
    @staticmethod
    def criar_documento(nome_arquivo, tipo_arquivo, conteudo_binario, metadados=None):
        # Implementação...
```

### Adaptadores

Utilizamos adaptadores para isolar a integração com serviços externos:

```python
class HuggingFaceEmbeddingAdapter:
    def __init__(self, model_name, device, normalize):
        # Inicialização...
    
    def embed_text(self, text):
        # Implementação...
```

## Guia para Adicionar Novos Recursos

### Adicionar um Novo Endpoint

1. Crie um arquivo para o endpoint em `api/endpoints/` ou adicione a uma definição existente
2. Defina modelos Pydantic para requisição/resposta
3. Implemente a lógica do endpoint utilizando serviços existentes
4. Registre o endpoint no roteador apropriado
5. Atualize a documentação em `docs/api-reference.md`

Exemplo:
```python
@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_text(
    request: AnalysisRequest,
    rag_service: RAGService = Depends(get_rag_svc)
):
    # Implementação...
```

### Adicionar um Novo Serviço

1. Crie um arquivo para o serviço em `core/services/`
2. Implemente a classe de serviço e seus métodos
3. Adicione uma função factory para injeção de dependência
4. Registre o serviço em `core/__init__.py` (se necessário)

Exemplo:
```python
class AnalysisService:
    def __init__(self):
        self.embedding_service = get_embedding_service()
    
    async def analyze_content(self, text):
        # Implementação...

_analysis_service_instance = None

def get_analysis_service():
    global _analysis_service_instance
    if _analysis_service_instance is None:
        _analysis_service_instance = AnalysisService()
    return _analysis_service_instance
```

## Contribuindo com a Documentação

A documentação deve ser mantida atualizada à medida que o código evolui. Siga estas diretrizes:

1. **Alterações em endpoints**: Atualize o arquivo `api-reference.md`
2. **Novos serviços ou módulos**: Documente-os no guia de desenvolvimento
3. **Alterações na configuração**: Atualize o arquivo `getting-started.md`
4. **Alterações no deployment**: Atualize o arquivo `deployment.md`

### Formatação da Documentação

- Use Markdown para toda a documentação
- Mantenha os exemplos de código atualizados
- Use cabeçalhos hierárquicos (# para título principal, ## para seções, etc.)
- Inclua exemplos de requisições e respostas para novos endpoints
- Documente parâmetros, tipos de dados e comportamentos esperados

## Teste e Qualidade de Código

### Executando Testes

```bash
cd backend
pytest
```

### Verificação de Estilo

```bash
flake8 backend
```

### Verificação de Tipos

```bash
mypy backend
```

## Workflow de Desenvolvimento

1. Crie um branch a partir de `main` para sua feature ou correção
2. Desenvolva e teste suas alterações
3. Atualize a documentação correspondente
4. Envie um pull request com uma descrição clara das alterações
5. Aguarde revisão e aprovação
6. Após aprovação, faça o merge para `main`

## Recursos Adicionais

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [pgvector Documentation](https://github.com/pgvector/pgvector)