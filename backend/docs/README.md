# CTA Value Tech - Documentação

Bem-vindo à documentação oficial da API CTA Value Tech, um sistema de valoração de tecnologias relacionadas ao Patrimônio Genético Nacional e Conhecimentos Tradicionais Associados.

## Sobre o Projeto

A API CTA Value Tech oferece serviços para consulta, análise e valoração de tecnologias associadas à biodiversidade brasileira. Utilizando uma arquitetura RAG (Retrieval-Augmented Generation), o sistema permite consultas inteligentes sobre documentos, gerando respostas contextualizadas e precisas.

## Conteúdo da Documentação

- [Referência da API](api-reference.md) - Documentação completa de endpoints, parâmetros e respostas
- [Guia de Início Rápido](getting-started.md) - Como começar a utilizar a API
- [Guia de Desenvolvimento](development-guide.md) - Guia para desenvolvedores que desejam contribuir
- [Instruções de Implantação](deployment.md) - Como implantar a API em diferentes ambientes

## Arquitetura

A API é construída com FastAPI e utiliza uma arquitetura em camadas:

- **API Layer**: Endpoints REST para interação com clientes
- **Service Layer**: Lógica de negócio e orquestração
- **Repository Layer**: Acesso e manipulação de dados
- **Infrastructure Layer**: Adaptadores para serviços externos (LLM, Embeddings)

A base de dados utiliza PostgreSQL com pgvector para armazenamento e busca eficiente de embeddings vetoriais.

## Atualização da Documentação

Esta documentação é mantida como parte do código-fonte e evolui junto com ele. Para cada nova funcionalidade ou modificação na API, a documentação correspondente deve ser atualizada seguindo as diretrizes no [Guia de Contribuição](development-guide.md#contribuindo-com-a-documentação).