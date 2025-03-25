"""
Serviço de Retrieval-Augmented Generation (RAG).
"""

import logging
import time
from typing import List, Dict, Any, Optional
from core.config import get_settings
from .embedding_service import get_embedding_service
from .llm_service import get_llm_service
from db.repositories.chunk_repository import ChunkRepository
from db.queries.hybrid_search import realizar_busca_hibrida, rerank_results
from processors.normalizers.text_normalizer import clean_query

logger = logging.getLogger(__name__)


class RAGService:
    """
    Serviço de Retrieval-Augmented Generation.

    Orquestra o processo completo de RAG:
    1. Preparação e limpeza da consulta
    2. Geração de embeddings
    3. Recuperação de documentos relevantes
    4. Montagem do contexto para o LLM
    5. Geração da resposta pelo LLM
    """

    def __init__(self):
        """
        Inicializa o serviço RAG.
        """
        self.settings = get_settings()
        self.embedding_service = get_embedding_service()
        self.llm_service = get_llm_service()

    async def process_query(
        self,
        query: str,
        filtro_documentos: Optional[List[int]] = None,
        max_results: Optional[int] = None,
        vector_weight: Optional[float] = None,
        include_debug_info: bool = False,
    ) -> Dict[str, Any]:
        """
        Processa uma consulta usando o pipeline RAG completo.

        Args:
            query: Consulta do usuário
            filtro_documentos: IDs de documentos para filtrar (opcional)
            max_results: Número máximo de resultados (opcional)
            vector_weight: Peso da busca vetorial vs. textual (opcional)
            include_debug_info: Se True, inclui informações de depuração na resposta

        Returns:
            dict: Resposta gerada e informações de depuração (se solicitado)
        """
        start_time = time.time()

        try:
            # 1. Preparar e limpar a consulta
            clean_query_text = clean_query(query)
            if not clean_query_text:
                return {"response": "Não entendi sua consulta. Pode reformulá-la?"}

            # 2. Gerar embedding da consulta
            query_embedding = self.embedding_service.embed_text(clean_query_text)

            # 3. Recuperar documentos relevantes
            alpha = (
                vector_weight
                if vector_weight is not None
                else self.settings.VECTOR_SEARCH_WEIGHT
            )
            limit = (
                max_results if max_results is not None else self.settings.MAX_RESULTS
            )
            
            logger.info(f"Resultado variavel classe: {limit}")

            retrieved_chunks = realizar_busca_hibrida(
                query_text=clean_query_text,
                query_embedding=query_embedding,
                limite=limit,
                alpha=alpha,
                filtro_documentos=filtro_documentos,
                threshold=0.5,
            )

            # 4. Reranking para melhorar a relevância
            ranked_chunks = rerank_results(retrieved_chunks, clean_query_text)

            # 5. Preparar contexto para o LLM
            context = ""

            if not ranked_chunks:
                logger.warning(
                    f"Nenhum documento relevante encontrado para a consulta: '{query}'"
                )
                context = "Não foram encontrados documentos relevantes para esta consulta específica."
            else:
                for i, chunk in enumerate(ranked_chunks):
                    context += f"Contexto {i+1} [relevância: {chunk.combined_score:.2f}]\n{chunk.texto}\n\n"

            # 6. Construir o prompt para o LLM
            system_prompt = f"""Você é um assistente especializado em valoração de tecnologias relacionadas ao Patrimônio Genético Nacional e Conhecimentos Tradicionais Associados.

            Responda ao usuário usando as informações fornecidas nos documentos do contexto. Cada contexto tem uma pontuação de relevância associada a ele - contextos com pontuação mais alta são mais relevantes para o tópico atual.

            IMPORTANTE: 
            - Não mencione os "contextos" ou "documentos" na sua resposta. O usuário não sabe que você está consultando diferentes fontes.
            - Identifique e responda apropriadamente a saudações e interações sociais básicas sem tentar forçar informações técnicas.
            - Para consultas técnicas, apresente a informação de forma natural e fluida.

            Se realmente não houver informações suficientes nos contextos para responder adequadamente, você pode indicar isso de forma sutil, sugerindo que há limitações nas informações disponíveis, mas tente sempre fornecer valor com o que você tem.

            As respostas devem ser em português brasileiro formal, mantendo a terminologia técnica apropriada ao tema de biodiversidade, conhecimentos tradicionais e propriedade intelectual quando relevante.
            """

            # 7. Gerar resposta com o LLM
            llm_input = f"Documentos:\n{context}\n\nPergunta: {query}"

            response = await self.llm_service.generate_text(
                system_prompt=system_prompt, user_prompt=llm_input
            )

            # 8. Preparar resultado
            processing_time = time.time() - start_time

            result = {"response": response, "processing_time": processing_time}

            # Adicionar informações de depuração se solicitado
            if include_debug_info:
                debug_info = {
                    "query": query,
                    "clean_query": clean_query_text,
                    "num_results": len(ranked_chunks),
                    "sources": [chunk.arquivo_origem for chunk in ranked_chunks],
                    "scores": [
                        round(chunk.combined_score, 3) for chunk in ranked_chunks
                    ],
                }
                result["debug_info"] = debug_info

            return result

        except Exception as e:
            logger.error(f"Erro ao processar consulta RAG: {str(e)}", exc_info=True)
            return {
                "response": "Desculpe, ocorreu um erro ao processar sua consulta. Por favor, tente novamente.",
                "error": str(e),
            }

    def get_similar_questions(self, query: str, limit: int = 5) -> List[str]:
        """
        Retorna perguntas similares à consulta do usuário.
        Útil para sugestões de perguntas relacionadas.

        Args:
            query: Consulta do usuário
            limit: Número máximo de perguntas a retornar

        Returns:
            list: Lista de perguntas similares
        """
        # Implementação simplificada - em uma versão real,
        # poderíamos ter um banco de perguntas frequentes com embeddings
        # e fazer busca por similaridade

        # Por enquanto, retornamos uma lista estática
        return [
            "O que é CTA Value Tech?",
            "Como funciona a valoração de tecnologias com acesso ao PGN?",
            "Quais são os princípios da Convenção sobre a Diversidade Biológica?",
            "Como são calculados os royalties da sociobiodiversidade?",
            "O que são Conhecimentos Tradicionais Associados?",
        ][:limit]


# Instância singleton para uso em toda a aplicação
_rag_service_instance: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """
    Retorna a instância do serviço RAG.

    Returns:
        RAGService: Instância do serviço
    """
    global _rag_service_instance

    if _rag_service_instance is None:
        _rag_service_instance = RAGService()

    return _rag_service_instance
