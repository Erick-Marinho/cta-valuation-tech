"""
Chunker semântico para divisão de texto inteligente.
"""
import logging
import re
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from ..normalizers.text_normalizer import normalize_text

logger = logging.getLogger(__name__)

def create_semantic_chunks(text: str, chunk_size: int = 800, chunk_overlap: int = 100) -> List[str]:
    """
    Divide o texto em chunks semânticos, preservando a estrutura do documento.
    Tenta identificar cabeçalhos e seções para manter a estrutura semântica.
    
    Args:
        text (str): Texto completo do documento
        chunk_size (int): Tamanho máximo de cada chunk
        chunk_overlap (int): Sobreposição entre chunks consecutivos
        
    Returns:
        list: Lista de chunks semânticos
    """
    # Verificar se o texto está vazio
    if not text or not text.strip():
        logger.warning("Texto vazio fornecido para chunking semântico")
        return []
    
    logger.info(f"Iniciando chunking semântico. Tamanho do texto: {len(text)} caracteres")
    
    # Tentar identificar se o documento tem uma estrutura com cabeçalhos
    has_headers = any(marker in text for marker in ["# ", "## ", "### ", "#### ", "Capítulo ", "Seção "])
    
    if has_headers:
        logger.info("Detectada estrutura com cabeçalhos, usando MarkdownHeaderTextSplitter")
        
        # Usar splitter baseado em headers do markdown para preservar a estrutura
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
            # Adiciona regex para match case-insensitive de cabeçalhos comuns
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
        except Exception as e:
            logger.error(f"Erro ao processar cabeçalhos, fallback para chunking simples: {e}")
            has_headers = False  # Forçar o fallback para chunking simples
            chunks = []
    
    if not has_headers:
        logger.info("Sem estrutura de cabeçalhos, usando RecursiveCharacterTextSplitter")
        
        # Para documentos sem estrutura clara de cabeçalhos, usar chunking tradicional
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        chunks = text_splitter.split_text(text)
        
        # Tentar identificar e preservar parágrafos completos
        refined_chunks = []
        for chunk in chunks:
            # Se o chunk for muito pequeno e parecer incompleto, tente expandir
            if len(chunk) < chunk_size * 0.5 and not chunk.endswith("."):
                # Buscar o próximo ponto final para completar o parágrafo
                dot_position = text.find(".", text.find(chunk) + len(chunk))
                if dot_position != -1 and dot_position - text.find(chunk) < chunk_size * 1.5:
                    refined_chunk = text[text.find(chunk):dot_position + 1]
                    refined_chunks.append(refined_chunk)
                else:
                    refined_chunks.append(chunk)
            else:
                refined_chunks.append(chunk)
        
        chunks = refined_chunks
    
    # Limpar e normalizar os chunks finais
    final_chunks = []
    for chunk in chunks:
        # Normalizar o texto do chunk
        clean_chunk = normalize_text(chunk)
        
        # Verificar se o chunk tem conteúdo significativo
        if len(clean_chunk.strip()) > 50:  # Ignorar chunks muito pequenos
            final_chunks.append(clean_chunk)
    
    logger.info(f"Chunking concluído. Gerados {len(final_chunks)} chunks")
    
    return final_chunks