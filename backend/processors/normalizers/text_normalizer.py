"""
Normalização e limpeza de texto para processamento.
"""

import re
import logging
import unicodedata
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """
    Normaliza o texto extraído para melhorar a qualidade.

    Args:
        text: Texto original extraído

    Returns:
        str: Texto normalizado
    """
    if not text:
        return ""

    # Remover caracteres nulos e de controle
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)

    # Normalizar espaços em branco (sem colapsar quebras de linha)
    text = re.sub(r"[ \t]+", " ", text)

    # Normalizar quebras de linha
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Normalizar múltiplas quebras de linha
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")

    # Normalizar capitalização se necessário
    uppercase_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
    if uppercase_ratio > 0.3:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        sentences = [s.capitalize() for s in sentences if s]
        text = " ".join(sentences)

    # Remover espaços em branco no início e fim
    text = text.strip()

    return text


def clean_text_for_embedding(text: str) -> str:
    """
    Limpa o texto para fins de embedding, mantendo apenas o conteúdo relevante.

    Args:
        text: Texto a ser limpo

    Returns:
        str: Texto limpo
    """
    if not text:
        return ""

    # Converter para minúsculas
    text = text.lower()

    # Normalizar unicode
    text = unicodedata.normalize("NFKC", text)

    # Remover URLs
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)

    # Remover emails
    text = re.sub(r"\S+@\S+", " ", text)

    # Remover números isolados (mas não números que fazem parte de palavras)
    text = re.sub(r"\b\d+\b", " ", text)

    # Remover pontuação repetida
    text = re.sub(r"([.!?]){2,}", r"\1", text)

    # Normalizar espaços
    text = re.sub(r"\s+", " ", text)

    # Remover espaços no início e fim
    text = text.strip()

    return text


def clean_query(query: str) -> str:
    """
    Limpa e normaliza a consulta do usuário para busca.

    Args:
        query: Consulta original do usuário

    Returns:
        str: Consulta limpa e normalizada
    """
    if not query:
        return ""

    # Normalizar unicode
    query = unicodedata.normalize("NFKC", query)

    # Remover caracteres especiais, mantendo palavras, números e pontuação básica
    query = re.sub(r"[^\w\s.!?]+", " ", query, flags=re.UNICODE)

    # Normalizar espaços
    query = re.sub(r"\s+", " ", query)

    # Remover espaços no início e fim
    query = query.strip()

    return query


def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    Extrai palavras-chave do texto para indexação ou busca.

    Args:
        text: Texto para extração de palavras-chave
        max_keywords: Número máximo de palavras-chave a extrair

    Returns:
        list: Lista de palavras-chave
    """
    if not text:
        return []

    # Normalizar e limpar o texto
    cleaned_text = clean_text_for_embedding(text.lower())

    # Lista de stopwords em português
    stopwords = {
        "a",
        "ao",
        "aos",
        "aquela",
        "aquelas",
        "aquele",
        "aqueles",
        "aquilo",
        "as",
        "até",
        "com",
        "como",
        "da",
        "das",
        "de",
        "dela",
        "delas",
        "dele",
        "deles",
        "depois",
        "do",
        "dos",
        "e",
        "ela",
        "elas",
        "ele",
        "eles",
        "em",
        "entre",
        "era",
        "eram",
        "éramos",
        "essa",
        "essas",
        "esse",
        "esses",
        "esta",
        "estas",
        "este",
        "estes",
        "eu",
        "foi",
        "fomos",
        "for",
        "foram",
        "fosse",
        "fossem",
        "fui",
        "há",
        "isso",
        "isto",
        "já",
        "lhe",
        "lhes",
        "mais",
        "mas",
        "me",
        "mesmo",
        "meu",
        "meus",
        "minha",
        "minhas",
        "muito",
        "na",
        "não",
        "nas",
        "nem",
        "no",
        "nos",
        "nós",
        "nossa",
        "nossas",
        "nosso",
        "nossos",
        "num",
        "numa",
        "o",
        "os",
        "ou",
        "para",
        "pela",
        "pelas",
        "pelo",
        "pelos",
        "por",
        "qual",
        "quando",
        "que",
        "quem",
        "são",
        "se",
        "seja",
        "sejam",
        "sejamos",
        "sem",
        "será",
        "serão",
        "seria",
        "seriam",
        "seríamos",
        "seu",
        "seus",
        "só",
        "somos",
        "sou",
        "sua",
        "suas",
        "também",
        "te",
        "tem",
        "tém",
        "temos",
        "tenha",
        "tenham",
        "tenhamos",
        "tenho",
        "terá",
        "terão",
        "terei",
        "teremos",
        "teria",
        "teriam",
        "teríamos",
        "teu",
        "teus",
        "teve",
        "tinha",
        "tinham",
        "tínhamos",
        "tive",
        "tivemos",
        "tiver",
        "tivera",
        "tiveram",
        "tivéramos",
        "tiverem",
        "tivermos",
        "tu",
        "tua",
        "tuas",
        "um",
        "uma",
        "você",
        "vocês",
        "vos",
    }

    # Dividir em palavras e filtrar stopwords
    words = [
        w
        for w in re.findall(r"\b\w+\b", cleaned_text)
        if w not in stopwords and len(w) > 2
    ]

    # Contar frequência das palavras
    word_freq = {}
    for word in words:
        if word in word_freq:
            word_freq[word] += 1
        else:
            word_freq[word] = 1

    # Ordenar por frequência e retornar as mais frequentes
    keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [k for k, v in keywords[:max_keywords]]


def analyze_text(text: str) -> Dict[str, Any]:
    """
    Analisa o texto e retorna estatísticas e metadados.

    Args:
        text: Texto a ser analisado

    Returns:
        dict: Estatísticas e metadados do texto
    """
    if not text:
        return {
            "word_count": 0,
            "char_count": 0,
            "sentence_count": 0,
            "paragraph_count": 0,
            "avg_word_length": 0,
            "language_hint": None,
            "keywords": [],
        }

    # Contagem básica
    char_count = len(text)
    word_count = len(re.findall(r"\b\w+\b", text))
    sentence_count = (
        len(re.findall(r"[.!?]+", text)) + 1
    )  # +1 para incluir a última sentença
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    paragraph_count = len(paragraphs)

    # Média de comprimento de palavras
    words = re.findall(r"\b\w+\b", text)
    avg_word_length = sum(len(word) for word in words) / max(len(words), 1)

    # Tentar detectar idioma (simplificado)
    pt_indicators = [
        "de",
        "que",
        "para",
        "com",
        "não",
        "uma",
        "os",
        "no",
        "se",
        "na",
        "por",
        "mais",
    ]
    en_indicators = [
        "the",
        "and",
        "to",
        "of",
        "in",
        "is",
        "that",
        "for",
        "you",
        "with",
        "on",
        "by",
    ]

    pt_count = sum(1 for word in words if word.lower() in pt_indicators)
    en_count = sum(1 for word in words if word.lower() in en_indicators)

    language_hint = None
    if pt_count > en_count:
        language_hint = "pt"
    elif en_count > pt_count:
        language_hint = "en"

    # Extrair palavras-chave
    keywords = extract_keywords(text)

    # Identificar padrões de formatação
    has_bullet_points = bool(re.search(r"^\s*[\*\-•]\s+", text, re.MULTILINE))
    has_numbering = bool(re.search(r"^\s*\d+[.)]\s+", text, re.MULTILINE))
    has_headings = bool(re.search(r"^\s*#{1,6}\s+", text, re.MULTILINE))

    return {
        "word_count": word_count,
        "char_count": char_count,
        "sentence_count": sentence_count,
        "paragraph_count": paragraph_count,
        "avg_word_length": round(avg_word_length, 1),
        "language_hint": language_hint,
        "keywords": keywords,
        "has_bullet_points": has_bullet_points,
        "has_numbering": has_numbering,
        "has_headings": has_headings,
    }
