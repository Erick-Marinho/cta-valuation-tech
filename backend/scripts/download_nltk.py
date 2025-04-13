import nltk
import logging
import sys # Para saída de erro

# Configurar um logger básico para o script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_nltk_data():
    """
    Baixa os pacotes de dados necessários do NLTK.
    """
    packages = ['punkt', 'punkt_tab'] # Lista de pacotes necessários
    logger.info(f"Tentando baixar pacotes NLTK: {', '.join(packages)}")

    all_successful = True
    for package in packages:
        try:
            logger.info(f"Baixando pacote: {package}...")
            # O download pode demorar um pouco
            if nltk.download(package, quiet=True): # quiet=True evita a GUI se disponível
                 logger.info(f"Pacote '{package}' baixado ou já existente com sucesso.")
            else:
                 # nltk.download retorna False se o download falhar por algum motivo
                 logger.error(f"Falha ao baixar pacote '{package}'. Verifique a conexão ou o nome do pacote.")
                 all_successful = False
        except Exception as e:
            logger.error(f"Erro inesperado ao tentar baixar pacote '{package}': {e}", exc_info=True)
            all_successful = False

    if not all_successful:
        logger.error("Nem todos os pacotes NLTK foram baixados com sucesso. Verifique os logs.")
        # Sair com código de erro para potencialmente falhar o build do Docker
        sys.exit(1)
    else:
        logger.info("Todos os pacotes NLTK necessários foram verificados/baixados.")

if __name__ == "__main__":
    download_nltk_data()
    