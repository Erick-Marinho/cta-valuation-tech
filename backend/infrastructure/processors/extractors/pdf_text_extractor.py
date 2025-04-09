from typing import Tuple, Dict, Any
import logging
import asyncio

# Importar a Interface da Aplicação
from application.interfaces.text_extractor import TextExtractor
# Importar a implementação concreta (agora dentro da infraestrutura)
from .pdf_extractor import PDFExtractor # Assumindo que pdf_extractor.py está no mesmo dir
from ..normalizers.text_normalizer import normalize_text

logger = logging.getLogger(__name__)

class PdfTextExtractor(TextExtractor):
    """ Implementação de TextExtractor usando a biblioteca PyMuPDF (via PDFExtractor). """

    async def extract(self, file_content: bytes, file_type: str) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
        """ Extrai texto de PDFs. Ignora file_type se não for 'pdf'. """
        if file_type.lower() != 'pdf':
            logger.warning(f"PdfTextExtractor chamado com tipo de arquivo não suportado: {file_type}. Retornando vazio.")
            # Ou poderia lançar uma exceção se apenas PDFs são esperados
            # raise ValueError(f"PdfTextExtractor só suporta 'pdf', recebeu '{file_type}'")
            return "", {}, {}

        try:
            # Chamar a lógica de extração original.
            # Se PDFExtractor.extract_all for síncrono, precisa de asyncio.to_thread
            # Vamos assumir que é síncrono por enquanto:
            # text, metadata, structure = PDFExtractor.extract_all(file_content)

            # Usando asyncio.to_thread para chamadas síncronas
            def sync_extract():
                return PDFExtractor.extract_all(file_content)

            # Executar a extração síncrona em um thread separado
            text, metadata, structure = await asyncio.to_thread(sync_extract)

            logger.info(f"Texto extraído do PDF. Tamanho: {len(text)}")
            return text, metadata or {}, structure or {}
        except Exception as e:
            logger.exception(f"Erro ao extrair texto do PDF: {e}")
            # Relançar como uma exceção genérica ou específica da extração
            raise RuntimeError(f"Falha na extração de PDF: {e}") from e
