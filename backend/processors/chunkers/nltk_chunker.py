import re
import nltk
nltk.download('punkt')
from nltk.tokenize import sent_tokenize

def clean_text(text):
    """Remove metadados indesejados."""
    text = re.sub(r"\[Página \d+\]", "", text)  # Remove [Página X]
    text = re.sub(r"Disponível em:.*", "", text)  # Remove URLs
    return text.strip()

def create_nltk_chunks(text, chunk_size=800, overlap=200):
    """Divide o texto em chunks respeitando frases e parágrafos."""
    sentences = sent_tokenize(text)  # Tokeniza por frases
    chunks = []
    chunk = []
    current_length = 0

    for sentence in sentences:
        sentence_length = len(sentence.split())
        if current_length + sentence_length > chunk_size:
            chunks.append(" ".join(chunk))
            chunk = chunk[-(overlap//5):]  # Mantém um overlap proporcional
            current_length = sum(len(s.split()) for s in chunk)
        chunk.append(sentence)
        current_length += sentence_length

    if chunk:
        chunks.append(" ".join(chunk))  # Adiciona o último chunk

    return chunks

# Exemplo de uso
#texto = """Seu texto original aqui..."""
#texto_limpo = clean_text(texto)
#chunks = create_nltk_chunks(texto_limpo)
