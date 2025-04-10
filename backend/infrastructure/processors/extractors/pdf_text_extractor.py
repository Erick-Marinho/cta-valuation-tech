from typing import Tuple, Dict, Any, List
import logging
import asyncio
import io # Importar io
import hashlib # <-- Importar hashlib

# Importar PyMuPDF (fitz)
try:
    import fitz # PyMuPDF
except ImportError:
    logging.error("PyMuPDF (fitz) não está instalado. 'pip install pymupdf'")
    fitz = None

# Importar a Interface da Aplicação
from application.interfaces.text_extractor import TextExtractor
# Importar a implementação concreta (agora dentro da infraestrutura)
from .pdf_extractor import PDFExtractor # Assumindo que pdf_extractor.py está no mesmo dir
from ..normalizers.text_normalizer import normalize_text

logger = logging.getLogger(__name__)

class PdfTextExtractor(TextExtractor):
    """
    Implementação de TextExtractor para arquivos PDF usando PyMuPDF (fitz).
    """

    async def extract_text(self, file_content: bytes, file_type: str) -> List[Dict[str, Any]]:
        """
        Extrai texto de um conteúdo de arquivo PDF, página por página.

        Retorna uma lista de dicionários, um para cada página,
        contendo 'page_number' e 'text'.
        """
        if file_type.lower() != "pdf":
            raise NotImplementedError(f"Tipo de arquivo '{file_type}' não suportado por PdfTextExtractor.")
        if not fitz:
             raise RuntimeError("Biblioteca PyMuPDF (fitz) não está disponível.")

        pages_data = []
        try:
            # Abrir o PDF a partir do conteúdo binário em memória
            pdf_document = fitz.open(stream=io.BytesIO(file_content), filetype="pdf")

            # Função síncrona para processar o documento
            def sync_extract():
                extracted_pages = []
                logger.info(f"Processando PDF com {len(pdf_document)} páginas...")
                for page_num_zero_based in range(len(pdf_document)):
                    page = pdf_document.load_page(page_num_zero_based)
                    page_text = page.get_text("text", sort=True) # Extrai texto simples, ordenado
                    page_number_one_based = page_num_zero_based + 1
                    extracted_pages.append({
                        "page_number": page_number_one_based,
                        "text": page_text.strip() # Remover espaços em branco extras
                    })
                    # Log a cada X páginas para não poluir muito
                    if page_number_one_based % 20 == 0:
                         logger.info(f"Extraído texto até a página {page_number_one_based}...")
                logger.info("Extração de texto de todas as páginas concluída.")
                return extracted_pages

            # Executar a função síncrona em um thread separado
            pages_data = await asyncio.to_thread(sync_extract)

            pdf_document.close() # Fechar o documento

        except Exception as e:
            logger.error(f"Erro ao extrair texto do PDF: {e}", exc_info=True)
            # Relançar ou retornar lista vazia? Relançar parece mais correto.
            raise RuntimeError(f"Erro durante a extração de texto do PDF: {e}") from e

        return pages_data

    async def extract_document_metadata(self, file_content: bytes, file_type: str) -> Dict[str, Any]:
        """ Extrai metadados gerais de arquivos PDF. """
        if file_type.lower() != 'pdf':
            logger.warning(f"PdfTextExtractor.extract_document_metadata chamado com tipo de arquivo não suportado: {file_type}. Retornando vazio.")
            return {}
        if not fitz:
             raise RuntimeError("Biblioteca PyMuPDF (fitz) não está disponível.")

        try:
            # Usar asyncio.to_thread para a chamada síncrona do PDFExtractor original
            def sync_extract_meta():
                # PDFExtractor.extract_metadata é um staticmethod
                return PDFExtractor.extract_metadata(file_content)

            extracted_metadata = await asyncio.to_thread(sync_extract_meta)
            logger.info(f"Metadados extraídos do PDF.")
            # Retornar metadados extraídos ou um dicionário vazio se a extração retornar None/False
            return extracted_metadata if extracted_metadata else {}

        except Exception as e:
            logger.exception(f"Erro ao extrair metadados do PDF: {e}")
            # Retornar dicionário vazio ou com erro? Vazio é mais seguro para o fluxo.
            return {"metadata_extraction_error": str(e)}

    # Método 'extract' pode ser removido se não for mais usado diretamente
    # async def extract(self, file_content: bytes, file_type: str) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
    #     ...
