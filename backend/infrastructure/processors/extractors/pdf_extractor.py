"""
Extração de texto a partir de documentos PDF.
"""

import logging
import fitz  # PyMuPDF
from typing import Dict, Any, List, Tuple
from ..normalizers.text_normalizer import normalize_text

logger = logging.getLogger(__name__)


class PDFExtractor:
    """
    Extrai texto e metadados de documentos PDF.

    Utiliza PyMuPDF (fitz) para extração de alta qualidade.
    """

    @staticmethod
    def extract_text(file_content: bytes) -> str:
        """
        Extrai texto de um arquivo PDF.

        Args:
            file_content: Conteúdo binário do arquivo PDF

        Returns:
            str: Texto extraído e normalizado
        """
        text = ""
        try:
            # Criar um documento a partir dos bytes
            doc = fitz.open(stream=file_content, filetype="pdf")

            # Extrair texto de cada página
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text("text")

                # Adicionar informação da página para melhor contextualização
                if page_text.strip():
                    text += f"[Página {page_num + 1}]\n{page_text}\n\n"

            # Normalizar o texto
            text = normalize_text(text)

            # Registrar amostra para depuração (limitada a 300 caracteres)
            sample = text[:300] + "..." if len(text) > 300 else text
            logger.debug(f"Amostra de texto extraído: {sample}")

            return text

        except Exception as e:
            logger.error(f"Erro na extração de texto PDF: {str(e)}")
            return ""

    @staticmethod
    def extract_metadata(file_content: bytes) -> Dict[str, Any]:
        """
        Extrai metadados de um arquivo PDF.

        Args:
            file_content: Conteúdo binário do arquivo PDF

        Returns:
            dict: Metadados extraídos
        """
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")

            metadata = {
                "page_count": len(doc),
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
                "keywords": doc.metadata.get("keywords", ""),
                "creator": doc.metadata.get("creator", ""),
                "producer": doc.metadata.get("producer", ""),
                "format": "PDF " + doc.metadata.get("format", ""),
                "encryption": doc.metadata.get("encryption", None) is not None,
                "has_toc": doc.get_toc() is not None and len(doc.get_toc()) > 0,
            }

            return metadata

        except Exception as e:
            logger.error(f"Erro na extração de metadados PDF: {str(e)}")
            return {"error": str(e)}

    @staticmethod
    def extract_structure(file_content: bytes) -> List[Dict[str, Any]]:
        """
        Extrai a estrutura do documento (títulos, capítulos, etc.).

        Args:
            file_content: Conteúdo binário do arquivo PDF

        Returns:
            list: Lista de elementos estruturais do documento
        """
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")

            # Tentar extrair TOC (Table of Contents)
            toc = doc.get_toc()
            if toc:
                structure = []
                for item in toc:
                    level, title, page = item
                    structure.append({"level": level, "title": title, "page": page})
                return structure

            # Se não tiver TOC, fazer uma análise heurística de cabeçalhos
            # Isso é uma simplificação - uma implementação real seria mais sofisticada
            structure = []
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                blocks = page.get_text("dict")["blocks"]

                for block in blocks:
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line["spans"]:
                                # Heurística simples: texto com fonte grande e poucas palavras
                                # poderia ser um cabeçalho
                                text = span["text"].strip()
                                font_size = span["size"]

                                if (
                                    font_size > 12
                                    and len(text) < 100
                                    and len(text.split()) < 15
                                ):

                                    # Estimar o nível do cabeçalho com base no tamanho da fonte
                                    level = 1
                                    if font_size < 16:
                                        level = 2
                                    elif font_size < 14:
                                        level = 3

                                    structure.append(
                                        {
                                            "level": level,
                                            "title": text,
                                            "page": page_num + 1,
                                            "font_size": font_size,
                                            "inferred": True,  # Indicar que foi inferido, não do TOC
                                        }
                                    )

            return structure

        except Exception as e:
            logger.error(f"Erro na extração de estrutura PDF: {str(e)}")
            return []

    @staticmethod
    def extract_all(
        file_content: bytes,
    ) -> Tuple[str, Dict[str, Any], List[Dict[str, Any]]]:
        """
        Extrai texto, metadados e estrutura de um arquivo PDF.

        Args:
            file_content: Conteúdo binário do arquivo PDF

        Returns:
            tuple: (texto, metadados, estrutura)
        """
        text = PDFExtractor.extract_text(file_content)
        metadata = PDFExtractor.extract_metadata(file_content)
        structure = PDFExtractor.extract_structure(file_content)

        return text, metadata, structure
