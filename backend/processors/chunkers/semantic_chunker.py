"""
Chunker semântico para divisão de texto inteligente.
"""
import logging
import re
import math
from typing import List, Dict, Any, Tuple
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from ..normalizers.text_normalizer import normalize_text

logger = logging.getLogger(__name__)

def determine_best_strategy(text: str) -> str:
    """
    Determina a melhor estratégia de chunking com base nas características do documento.
    
    Args:
        text (str): Texto do documento
        
    Returns:
        str: Nome da estratégia recomendada
    """
    
    # Verificar se tem estrutura de cabeçalhos
    has_headers = any(marker in text for marker in ["# ", "## ", "### ", "#### ", "Capítulo ", "Seção "])
    
    # Verificar se tem estrutura clara de parágrafos
    has_paragraph_structure = len(re.findall(r'\n\n', text)) > len(text) / 1000
    
    # Verificar o comprimento do documento
    is_long_document = len(text) > 10000
    
    # Aplicar regras heurísticas baseadas no artigo
    if has_headers and is_long_document:
        return "header_based"  # Bom para documentos estruturados longos
    elif has_paragraph_structure and not has_headers:
        return "paragraph"     # Bom para documentos com parágrafos claros
    else:
        return "hybrid"        # Abordagem mais robusta para casos gerais
    
def header_based_chunking(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """
    Chunking baseado em cabeçalhos para documentos bem estruturados.
    
    Args:
        text (str): Texto a ser dividido
        chunk_size (int): Tamanho máximo de cada chunk
        chunk_overlap (int): Sobreposição entre chunks
        
    Returns:
        list: Lista de chunks
    """
    logger.info("Aplicando chunking baseado em cabeçalhos")
    
    # Definir cabeçalhos para divisão
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
        ("####", "Header 4"),
    ]
    
    # Adicionar cabeçalhos específicos para documentos de valoração
    for keyword in ["Introdução", "Metodologia", "Valoração", "CTA", "Biodiversidade", 
                    "Conhecimento Tradicional", "Patrimônio Genético", "Royalties", 
                    "Repartição de Benefícios"]:
        pattern = f"^{keyword}\\s*[:.|)]"
        if re.search(pattern, text, re.MULTILINE | re.IGNORECASE):
            headers_to_split_on.append((f"{keyword}", f"Seção {keyword}"))
            
    # Criar o splitter de cabeçalhos
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    
    # Dividir o documento em seções baseadas em cabeçalhos
    try:
        sections = markdown_splitter.split_text(text)
        logger.info(f"Documento dividido em {len(sections)} seções")
        
        # Para cada seção, aplicar chunking por caracteres se for muito grande
        chunks = []
        for section in sections:
            # Obter o conteúdo e metadados do cabeçalho
            content = section.page_content
            metadata = section.metadata
            
            # Se o conteúdo for maior que o chunk_size, dividi-lo
            if len(content) > chunk_size:
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    separators=["\n\n", "\n", ". ", " ", ""]
                )
                sub_chunks = text_splitter.split_text(content)
                
                # Adicionar cada sub-chunk com os metadados do cabeçalho
                for i, sub_chunk in enumerate(sub_chunks):
                    # Prepend header information to each chunk for context
                    header_info = ""
                    for header_type, header_value in metadata.items():
                        if header_value:
                            header_info += f"{header_value}: "
                    
                    # Add the header info to the beginning of the chunk
                    enriched_chunk = f"{header_info.strip()}\n{sub_chunk}" if header_info else sub_chunk
                    chunks.append(enriched_chunk)
            else:
                # Se o conteúdo for pequeno o suficiente, adicionar como está
                header_info = ""
                for header_type, header_value in metadata.items():
                    if header_value:
                        header_info += f"{header_value}: "
                
                enriched_chunk = f"{header_info.strip()}\n{content}" if header_info else content
                chunks.append(enriched_chunk)
        
        return chunks
        
    except Exception as e:
        logger.error(f"Erro ao processar cabeçalhos: {e}")
        # Fallback para chunking por parágrafos
        return paragraph_based_chunking(text, chunk_size, chunk_overlap)
    
def paragraph_based_chunking(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """
    Chunking baseado em parágrafos com sobreposição inteligente.
    
    Args:
        text (str): Texto a ser dividido
        chunk_size (int): Tamanho máximo de cada chunk
        chunk_overlap (int): Sobreposição mínima entre chunks
        
    Returns:
        list: Lista de chunks
    """
    logger.info("Aplicando chunking baseado em parágrafos")
    
    # Dividir o texto em parágrafos
    paragraphs = re.split(r'\n\n+', text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    
    if not paragraphs:
        logger.warning("Nenhum parágrafo encontrado. Usando chunking simples.")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n", ". ", " ", ""]
        )
        return text_splitter.split_text(text)
    
    chunks = []
    current_chunk = ""
    current_paragraphs = []
    
    for paragraph in paragraphs:
        # Se adicionar este parágrafo ultrapassaria o tamanho máximo
        if len(current_chunk) + len(paragraph) > chunk_size and current_chunk:
            # Adicionar o chunk atual à lista
            chunks.append(current_chunk)
            
            # Calcular quantos parágrafos manter para a sobreposição
            overlap_size = 0
            paragraphs_to_keep = []
            
            # Começar do final e ir adicionando parágrafos até atingir o overlap desejado
            for p in reversed(current_paragraphs):
                if overlap_size + len(p) <= chunk_overlap:
                    paragraphs_to_keep.insert(0, p)
                    overlap_size += len(p)
                else:
                    break
            
            # Iniciar novo chunk com os parágrafos de sobreposição
            current_chunk = "\n\n".join(paragraphs_to_keep)
            current_paragraphs = paragraphs_to_keep
        
        # Adicionar o parágrafo atual
        if current_chunk:
            current_chunk += "\n\n" + paragraph
        else:
            current_chunk = paragraph
            
        current_paragraphs.append(paragraph)
    
    # Adicionar o último chunk se não estiver vazio
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

def hybrid_chunking(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """
    Estratégia híbrida que combina abordagens de cabeçalho e parágrafo.
    
    Args:
        text (str): Texto a ser dividido
        chunk_size (int): Tamanho máximo de cada chunk
        chunk_overlap (int): Sobreposição entre chunks
        
    Returns:
        list: Lista de chunks
    """
    logger.info("Aplicando chunking híbrido")
    
    # Primeiro, tenta dividir por cabeçalhos principais
    header_pattern = re.compile(r'^(#|##) .+$', re.MULTILINE)
    sections = []
    
    # Encontrar todos os cabeçalhos principais
    headers = list(header_pattern.finditer(text))
    
    if headers:
        # Dividir o texto em seções baseadas nos cabeçalhos principais
        for i in range(len(headers)):
            start = headers[i].start()
            end = headers[i+1].start() if i < len(headers) - 1 else len(text)
            sections.append(text[start:end])
    else:
        # Se não houver cabeçalhos principais, considerar o texto inteiro como uma seção
        sections = [text]
    
    # Para cada seção, aplicar divisão por parágrafos se necessário
    chunks = []
    for section in sections:
        # Se a seção for pequena o suficiente, mantê-la inteira
        if len(section) <= chunk_size:
            chunks.append(section)
        else:
            # Se for grande, aplicar chunking baseado em parágrafos
            section_chunks = paragraph_based_chunking(section, chunk_size, chunk_overlap)
            chunks.extend(section_chunks)
    
    return chunks

def evaluate_chunk_quality(chunks: List[str], original_text: str) -> Dict[str, float]:
    """
    Avalia a qualidade dos chunks gerados.
    
    Args:
        chunks (list): Lista de chunks
        original_text (str): Texto original
        
    Returns:
        dict: Métricas de qualidade
    """
    if not chunks:
        return {"coverage": 0, "avg_coherence": 0, "size_consistency": 0}
    
    metrics = {}
    
    # 1. Cobertura do texto (quanto do texto original está nos chunks)
    total_text = "".join(chunks)
    metrics["coverage"] = len(total_text) / max(len(original_text), 1)
    
    # 2. Coerência dos chunks
    coherence_scores = []
    for chunk in chunks:
        # Verificar características que indicam incoerência
        starts_with_conjunction = bool(re.match(r'\b(e|mas|porém|contudo|entretanto)\b', chunk.lower()))
        ends_abruptly = chunk.endswith(',') or chunk.endswith(':')
        
        # Calcular pontuação de coerência
        coherence = 1.0
        if starts_with_conjunction:
            coherence -= 0.3
        if ends_abruptly:
            coherence -= 0.3
            
        coherence_scores.append(max(0, coherence))
    
    metrics["avg_coherence"] = sum(coherence_scores) / len(coherence_scores)
    
    # 3. Consistência no tamanho dos chunks
    chunk_sizes = [len(chunk) for chunk in chunks]
    avg_size = sum(chunk_sizes) / len(chunk_sizes)
    size_variance = sum((s - avg_size)**2 for s in chunk_sizes) / len(chunk_sizes)
    metrics["size_consistency"] = 1.0 / (1.0 + math.sqrt(size_variance) / avg_size)
    
    return metrics

def create_semantic_chunks(
    text: str, 
    chunk_size: int = 800, 
    chunk_overlap: int = 100,
    strategy: str = "auto"  # Novo parâmetro para escolher a estratégia
) -> List[str]:
    """
    Divide o texto em chunks semânticos, preservando a estrutura do documento.
    Tenta identificar cabeçalhos e seções para manter a estrutura semântica.
    
    Args:
        text (str): Texto completo do documento
        chunk_size (int): Tamanho máximo de cada chunk
        chunk_overlap (int): Sobreposição entre chunks consecutivos
        strategy (str): Estratégia de chunking ("auto", "header_based", "paragraph", "hybrid")
        
    Returns:
        list: Lista de chunks semânticos
    """
    # Verificar se o texto está vazio
    if not text or not text.strip():
        logger.warning("Texto vazio fornecido para chunking semântico")
        return []
    
    logger.info(f"Iniciando chunking semântico. Tamanho do texto: {len(text)} caracteres. Estratégia: {strategy}")
    
    # Determinar a estratégia automaticamente se for "auto"
    if strategy == "auto":
        strategy = determine_best_strategy(text)
        logger.info(f"Estratégia automática selecionada: {strategy}")
    
    # Aplicar a estratégia adequada
    if strategy == "header_based":
        chunks = header_based_chunking(text, chunk_size, chunk_overlap)
    elif strategy == "paragraph":
        chunks = paragraph_based_chunking(text, chunk_size, chunk_overlap)
    elif strategy == "hybrid":
        chunks = hybrid_chunking(text, chunk_size, chunk_overlap)
    else:
        logger.warning(f"Estratégia desconhecida: {strategy}. Usando híbrida por padrão.")
        chunks = hybrid_chunking(text, chunk_size, chunk_overlap)
    
    # Limpar e normalizar os chunks finais
    final_chunks = []
    for chunk in chunks:
        # Normalizar o texto do chunk
        clean_chunk = normalize_text(chunk)
        
        # Verificar se o chunk tem conteúdo significativo
        if len(clean_chunk.strip()) > 50:  # Ignorar chunks muito pequenos
            final_chunks.append(clean_chunk)
    
    # Avaliar qualidade dos chunks
    quality_metrics = evaluate_chunk_quality(final_chunks, text)
    logger.info(f"Chunking concluído. Gerados {len(final_chunks)} chunks. Qualidade: {quality_metrics}")
    
    return final_chunks