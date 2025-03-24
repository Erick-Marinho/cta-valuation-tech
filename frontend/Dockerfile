FROM node:20-alpine

# Configurar diretório de trabalho
WORKDIR /app

# Copiar apenas os arquivos de dependências
COPY package.json ./

# Instalar dependências
RUN npm install

# Copiar o restante do código
COPY . .

# Definir variável para habilitar polling do sistema de arquivos
ENV WATCHPACK_POLLING=true
ENV CHOKIDAR_USEPOLLING=true

# Expor porta
EXPOSE 3000

# Iniciar aplicação em desenvolvimento
CMD ["npm", "run", "dev"]