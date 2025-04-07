"""
Extrator de texto para arquivos de texto simples.
"""

import logging
from typing import Dict, Any, Tuple
from ..normalizers.text_normalizer import normalize_text

logger = logging.getLogger(__name__)


class TextExtractor:
    """
    Extrai e processa texto de arquivos de texto simples.
    """

    @staticmethod
    def extract_text(file_content: bytes, encoding: str = "utf-8") -> str:
        """
        Extrai texto de um arquivo de texto simples.

        Args:
            file_content: Conteúdo binário do arquivo
            encoding: Codificação do texto (padrão: utf-8)

        Returns:
            str: Texto extraído e normalizado
        """
        try:
            # Converter bytes para string
            text = file_content.decode(encoding)

            # Normalizar o texto
            text = normalize_text(text)

            # Registrar amostra para depuração
            sample = text[:300] + "..." if len(text) > 300 else text
            logger.debug(f"Amostra de texto extraído: {sample}")

            return text

        except UnicodeDecodeError:
            # Tentar com detecção automática de encoding
            logger.warning(
                f"Falha ao decodificar com {encoding}, tentando auto-detecção"
            )
            try:
                # Detectar encodings comuns
                for enc in ["utf-8", "latin-1", "cp1252", "utf-16"]:
                    try:
                        text = file_content.decode(enc)
                        logger.info(f"Decodificação bem-sucedida com {enc}")

                        # Normalizar o texto
                        text = normalize_text(text)
                        return text
                    except UnicodeDecodeError:
                        continue

                # Se nenhum encoding funcionar, fallback para 'latin-1'
                text = file_content.decode("latin-1", errors="replace")
                logger.warning(
                    "Usando fallback para latin-1 com substituição de caracteres"
                )

                # Normalizar o texto
                text = normalize_text(text)
                return text

            except Exception as e:
                logger.error(f"Falha na extração de texto: {str(e)}")
                return ""

        except Exception as e:
            logger.error(f"Erro na extração de texto: {str(e)}")
            return ""

    @staticmethod
    def extract_metadata(file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Extrai metadados simples de um arquivo de texto.

        Args:
            file_content: Conteúdo binário do arquivo
            filename: Nome do arquivo

        Returns:
            dict: Metadados extraídos
        """
        # Para arquivo de texto simples, os metadados são básicos
        text = TextExtractor.extract_text(file_content)

        # Contar linhas, palavras e caracteres
        lines = text.count("\n") + 1
        words = len(text.split())
        chars = len(text)

        # Extrair extensão do arquivo
        extension = filename.split(".")[-1] if "." in filename else ""

        return {
            "filename": filename,
            "extension": extension,
            "size_bytes": len(file_content),
            "line_count": lines,
            "word_count": words,
            "char_count": chars,
            "content_type": f"text/{extension}" if extension else "text/plain",
        }

    @staticmethod
    def extract_all(file_content: bytes, filename: str) -> Tuple[str, Dict[str, Any]]:
        """
        Extrai texto e metadados de um arquivo de texto.

        Args:
            file_content: Conteúdo binário do arquivo
            filename: Nome do arquivo

        Returns:
            tuple: (texto, metadados)
        """
        text = TextExtractor.extract_text(file_content)
        metadata = TextExtractor.extract_metadata(file_content, filename)

        return text, metadata
