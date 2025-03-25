# cta-valuation-tech

# Iniciando a Aplicação

Este projeto utiliza Docker Compose para orquestrar os serviços necessários para rodar a aplicação. Siga os passos abaixo para iniciar a aplicação.

## Pré-requisitos

- Docker instalado: [Instruções de instalação](https://docs.docker.com/get-docker/)
- Docker Compose instalado: [Instruções de instalação](https://docs.docker.com/compose/install/)

## Passos para iniciar a aplicação

1. Clone o repositório:

   ```sh
   git clone https://github.com/seu-usuario/seu-repositorio.git
   cd seu-repositorio
   ```

2. Crie um arquivo `.env` na pasta `backend` com as variáveis de ambiente necessárias (se aplicável).

3. Inicie os serviços com Docker Compose:

   ```sh
   docker-compose up --build
   ```

   Isso irá construir as imagens Docker e iniciar os serviços definidos no arquivo [docker-compose.yml](http://_vscodecontentref_/2).

4. Acesse a aplicação:

   - Backend: [http://localhost:8000](http://localhost:8000)
   - Banco de Dados (PostgreSQL): [http://localhost:5432](http://localhost:5432)

## Serviços

- **Backend**: Serviço principal da aplicação, rodando um servidor Uvicorn.
- **Database**: Banco de dados PostgreSQL com a extensão pgvector.

## Volumes

- `pgdata`: Volume para persistência dos dados do PostgreSQL.

## Comandos Úteis

- Parar os serviços:

  ```sh
  docker-compose down
  ```

- Construir as imagens:

  ```sh
  docker-compose up --build
  ```

- Verificar logs dos serviços:

  ```sh
  docker-compose logs -f
  ```

## Estrutura do Projeto

- [backend](http://_vscodecontentref_/3): Código fonte do backend.
- [frontend](http://_vscodecontentref_/4): Código fonte do frontend (comentado no [docker-compose.yml](http://_vscodecontentref_/5)).
- [docker-compose.yml](http://_vscodecontentref_/6): Arquivo de configuração do Docker Compose.

## Notas

- Certifique-se de que as portas `8000` e `5432` estejam livres em sua máquina.
- Para customizar as variáveis de ambiente, edite o arquivo `.env` na pasta [backend](http://_vscodecontentref_/7).

---

Sinta-se à vontade para contribuir com o projeto ou abrir issues para relatar problemas.
