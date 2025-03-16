# Arquitetura Proposta para Refatoração do Backend

## Visão Geral

A refatoração proposta visa implementar uma arquitetura em camadas seguindo os princípios SOLID e Clean Architecture, separando as responsabilidades e tornando o código mais manutenível e testável.

## Estrutura de Diretórios Proposta

```
backend/
├── api/
│   ├── routes/
│   │   ├── document_routes.py
│   │   └── search_routes.py
│   ├── middlewares/
│   └── dependencies.py
├── core/
│   ├── config.py
│   └── exceptions.py
├── domain/
│   ├── models/
│   │   ├── document.py
│   │   └── chunk.py
│   ├── interfaces/
│   │   ├── document_repository.py
│   │   └── vector_service.py
│   └── value_objects/
├── infrastructure/
│   ├── database/
│   │   ├── connection.py
│   │   ├── repositories/
│   │   └── migrations/
│   └── services/
│       └── vector_service.py
├── application/
│   ├── services/
│   │   ├── document_service.py
│   │   └── search_service.py
│   ├── dtos/
│   └── interfaces/
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```

## Camadas e Responsabilidades

### 1. Domain Layer (domain/)

- Contém as entidades principais do negócio (Document, Chunk)
- Interfaces (abstrações) para repositórios e serviços
- Value Objects e regras de negócio core
- Não possui dependências externas

### 2. Application Layer (application/)

- Implementa casos de uso da aplicação
- Orquestra fluxos entre diferentes serviços
- DTOs para transferência de dados
- Depende apenas da camada de domínio

### 3. Infrastructure Layer (infrastructure/)

- Implementações concretas dos repositórios
- Serviços externos (vetorização, banco de dados)
- Configurações de banco de dados
- Implementações das interfaces definidas no domínio

### 4. API Layer (api/)

- Rotas e controllers
- Middlewares
- Injeção de dependências
- Tratamento de requisições HTTP

### 5. Core (core/)

- Configurações globais
- Exceções customizadas
- Utilitários compartilhados

## Princípios a Serem Seguidos

1. **Dependency Inversion Principle (DIP)**

   - Módulos de alto nível não devem depender de módulos de baixo nível
   - Ambos devem depender de abstrações

2. **Interface Segregation Principle (ISP)**

   - Criar interfaces específicas para cada tipo de cliente
   - Evitar interfaces genéricas e grandes

3. **Single Responsibility Principle (SRP)**

   - Cada classe/módulo deve ter apenas uma razão para mudar
   - Separar responsabilidades em classes distintas

4. **Open/Closed Principle (OCP)**
   - Entidades devem estar abertas para extensão, fechadas para modificação
   - Usar abstrações e injeção de dependência

## Benefícios Esperados

1. **Testabilidade**

   - Facilidade para criar testes unitários
   - Possibilidade de mock de dependências
   - Testes mais isolados e confiáveis

2. **Manutenibilidade**

   - Código mais organizado e previsível
   - Separação clara de responsabilidades
   - Facilidade para adicionar novas funcionalidades

3. **Escalabilidade**

   - Facilidade para adicionar novos serviços
   - Possibilidade de trocar implementações
   - Melhor gerenciamento de dependências

4. **Documentação**
   - Estrutura auto-documentada
   - Fluxos de dados mais claros
   - Facilidade para novos desenvolvedores

## Próximos Passos

1. Criar as interfaces base no domain layer
2. Implementar modelos e value objects
3. Desenvolver os serviços da application layer
4. Implementar repositórios na infrastructure layer
5. Refatorar as rotas existentes para a nova estrutura
6. Adicionar testes unitários e de integração
7. Documentar padrões e convenções
