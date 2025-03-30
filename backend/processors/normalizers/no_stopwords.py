import nltk
from nltk.corpus import stopwords

# Baixe as stopwords se necessário
nltk.download('stopwords')

# Obtenha stopwords em português
stop_words = set(stopwords.words('portuguese'))

def remove_stopwords(text):
    words = text.split()
    filtered_words = [word for word in words if word.lower() not in stop_words]
    return ' '.join(filtered_words)

# Aplique a função aos seus documentos
# processed_docs = [remove_stopwords(doc) for doc in documents]