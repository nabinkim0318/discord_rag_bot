# app/services/rag_service.py
import random
import time
from typing import Any, Dict, List, Optional, Tuple

from app.core.exceptions import RAGException
from app.core.logging import log_rag_operation, logger
from app.core.metrics import (
    record_rag_pipeline_latency,
    record_retrieval_hit,
    record_retriever_topk,
)
from app.core.retry import retry_openai, retry_weaviate

# Note: generate_answer import removed to avoid rag_agent dependency


def generate_answer(
    query: str,
    *,
    k_bm25: int = 20,
    k_vec: int = 20,
    k_final: int = 8,
    bm25_weight: float = 0.4,
    vec_weight: float = 0.6,
    mmr_lambda: float = 0.65,
    reranker: Optional[str] = None,
    prompt_version: str = "v1.1",
    stream: bool = False,
    filters_fts: Optional[str] = None,
    filters_weaviate: Optional[Dict[str, Any]] = None,
) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Mock implementation of generate_answer to avoid rag_agent dependency.
    In a real implementation, this would use the full RAG pipeline.
    """
    logger.warning("Using mock generate_answer - rag_agent not available")

    # Mock response
    answer = f"Mock response for query: {query[:50]}..."
    used_hits = [
        {
            "chunk_uid": "mock-chunk-1",
            "text": f"Mock context 1 for query: {query[:30]}...",
            "score": 0.95,
            "source": "mock_document.pdf",
            "metadata": {"page": 1, "section": "introduction"},
        },
        {
            "chunk_uid": "mock-chunk-2",
            "text": f"Mock context 2 for query: {query[:30]}...",
            "score": 0.87,
            "source": "mock_document.pdf",
            "metadata": {"page": 2, "section": "details"},
        },
    ]
    metadata = {
        "mock": True,
        "query": query,
        "k_bm25": k_bm25,
        "k_vec": k_vec,
        "k_final": k_final,
        "prompt_version": prompt_version,
    }

    return answer, used_hits, metadata


def get_embedding(query: str) -> List[float]:
    """
    Generate embedding from query (Mock implementation)
    In a real implementation, this would use OpenAI Embeddings API or \
    sentence-transformers
    """
    try:
        logger.debug(f"Generating embedding for query: {query[:50]}...")
        # Mock embedding: 768-dimensional vector
        embedding = [random.random() for _ in range(768)]
        logger.debug(f"Generated embedding with {len(embedding)} dimensions")
        return embedding
    except Exception as e:
        logger.error(f"Failed to generate embedding: {str(e)}")
        raise RAGException(f"Embedding generation failed: {str(e)}")


@retry_weaviate(max_attempts=3)
def search_similar_documents(query: str, top_k: int = 3) -> List[Dict]:
    """
    Search similar documents using Weaviate (with fallback)
    """
    try:
        logger.debug(f"Searching Weaviate for {top_k} similar documents")

        # Try to import and use Weaviate client
        try:
            from app.core.weaviate_client import weaviate_client

            documents = weaviate_client.search_similar(query, top_k)

            # Convert to expected format
            docs = []
            for doc in documents:
                docs.append(
                    {
                        "id": doc["id"],
                        "text": doc["content"],
                        "score": doc["certainty"],  # Weaviate certainty score
                        "source": doc["source"],
                        "metadata": doc["metadata"],
                        "query_id": doc["query_id"],
                    }
                )

            logger.debug(
                f"Found {len(docs)} documents with scores: \
                {[doc['score'] for doc in docs]}"
            )
            return docs

        except ImportError as e:
            logger.warning(f"Weaviate client not available: {str(e)}")
            return _mock_document_search(top_k)

    except Exception as e:
        logger.error(f"Document search failed: {str(e)}")
        # Fallback to mock implementation if Weaviate fails
        logger.warning("Falling back to mock document search")
        return _mock_document_search(top_k)


def _mock_document_search(top_k: int) -> List[Dict]:
    """Fallback mock document search"""
    return [
        {
            "id": f"mock_doc_{i}",
            "text": f"Mock context document {i} related to the query. \
            This contains relevant information that would help answer \
            the user's question.",
            "score": round(random.uniform(0.5, 1.0), 3),
            "source": f"mock_document_{i}.pdf",
            "metadata": {"type": "mock"},
            "query_id": None,
        }
        for i in range(top_k)
    ]


@retry_openai(max_attempts=3)
def call_llm(prompt: str) -> str:
    """
    Call LLM (Mock implementation)
    In a real implementation, this would use OpenAI GPT, \
    Anthropic Claude, or a local model
    """
    try:
        logger.debug(f"Calling LLM with prompt length: {len(prompt)}")
        time.sleep(1)  # Mock response delay
        answer = (
            "This is a mock response generated by the language model. "
            "The query was processed and a contextual answer has been generated "
            "based on the provided context documents."
        )
        logger.debug(f"LLM response generated: {len(answer)} characters")
        return answer
    except Exception as e:
        logger.error(f"LLM call failed: {str(e)}")
        raise RAGException(f"LLM call failed: {str(e)}")


def run_rag_pipeline(
    query: str,
    top_k: int = 5,
    *,
    user_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    request_id: Optional[str] = None,
    prompt_version: Optional[str] = "v1.1",
    use_rerank: bool = True,
    reranker: Optional[str] = "cohere",  # None|'cohere'|'jina'
    ab_test_group: Optional[str] = None,
) -> Tuple[str, List[str], Dict]:
    start = time.time()
    record_retriever_topk(top_k)

    try:
        # (필요 시 헤더 필터 → filters_fts/filters_weaviate로 전달)
        ans_or_stream, used_hits, meta = generate_answer(
            query,
            k_bm25=max(20, top_k * 3),
            k_vec=max(20, top_k * 3),
            k_final=top_k,
            reranker=(reranker if use_rerank else None),
            prompt_version=prompt_version or "v1.1",
            stream=False,
        )

        if isinstance(ans_or_stream, str):
            answer = ans_or_stream
        else:
            # stream=False로 호출했으니 여기 안옴
            answer = "".join(list(ans_or_stream))

        contexts = [h["text"] for h in used_hits]
        record_retrieval_hit(len(contexts) > 0)

        duration = time.time() - start
        record_rag_pipeline_latency(duration)
        log_rag_operation(
            query, True, duration, len(contexts), user_id, channel_id, request_id
        )

        # meta 확장
        meta.update(
            {
                "sources": [h.get("source") for h in used_hits],
                "uids": [h.get("chunk_uid") for h in used_hits],
                "pipeline_duration": round(duration, 3),
            }
        )

        return answer, contexts, meta

    except Exception as e:
        duration = time.time() - start
        record_rag_pipeline_latency(duration)
        log_rag_operation(
            query,
            False,
            duration,
            user_id=user_id,
            channel_id=channel_id,
            request_id=request_id,
        )
        logger.error(f"RAG pipeline error: {e}")
        from app.core.exceptions import RAGException

        raise RAGException(f"Generation pipeline failed: {e}")


# def run_rag_pipeline(
#     query: str,
#     top_k: int = 5,
#     *,
#     user_id: Optional[str] = None,
#     channel_id: Optional[str] = None,
#     request_id: Optional[str] = None,
#     # A/B 실험 파라미터
#     prompt_version: Optional[str] = None,
#     use_rerank: bool = False,
#     ab_test_group: Optional[str] = None,
# ) -> Tuple[str, List[str], Dict]:
#     """
#     Complete RAG pipeline execution

#     Args:
#         query: user question
#         top_k: number of documents to search

#     Returns:
#         Tuple[answer, contexts, metadata]
#     """
#     start_time = time.time()

#     try:
#         logger.info("Starting RAG pipeline for query: '{}'", query[:50])

#         # Record requested top_k distribution
#         record_retriever_topk(top_k)

#         # 1. Search similar documents using Weaviate
#         docs = search_similar_documents(query, top_k)
#         context_texts = [doc["text"] for doc in docs]

#         # Add request_id to context for tracing
#         if request_id:
#             logger.debug(
#                 "Searching documents for query with request_id: {}",
#                 request_id,
#                 extra={
#                     "request_id": request_id,
#                     "query": query,
#                     "top_k": top_k,
#                     "contexts_found": len(context_texts),
#                 },
#             )

#         # Record retrieval hit (whether any context was found)
#         record_retrieval_hit(len(context_texts) > 0)

#         # 2. A/B 실험: 프롬프트 버전 결정
#         if prompt_version is None:
#             if ab_test_group == "random":
#                 # 랜덤 버전 선택
#                 try:
#                     from rag_agent.generation.prompt_builder import prompt_builder

#                     prompt_version = prompt_builder.get_random_version()
#                 except ImportError:
#                     prompt_version = "v1.1"  # fallback
#             else:
#                 prompt_version = "v1.1"  # 기본 버전

#         # 3. Construct prompt with version management
#         try:
#             from rag_agent.generation.prompt_builder import build_prompt

#             prompt_data = build_prompt(context_texts, query, version=prompt_version)
#             prompt = prompt_data["prompt"]
#             prompt_metadata = prompt_data["metadata"]
#         except ImportError:
#             # Fallback to simple prompt
#             prompt = f"""Context Documents:
# {chr(10).join([f"- {text}" for text in context_texts])}

# Question: {query}

# Please provide a comprehensive answer based on the context documents above:"""
#             prompt_metadata = {"version": "fallback"}

#         # 4. Call LLM
#         if request_id:
#             logger.debug(
#                 "Calling LLM with request_id: {}",
#                 request_id,
#                 extra={
#                     "request_id": request_id,
#                     "prompt_length": len(prompt),
#                     "contexts_count": len(context_texts),
#                 },
#             )
#         answer = call_llm(prompt)

#         # 5. Construct metadata
#         duration = time.time() - start_time
#         metadata = {
#             "num_contexts": len(context_texts),
#             "retrieval_scores": [doc["score"] for doc in docs],
#             "sources": [doc["source"] for doc in docs],
#             "pipeline_duration": round(duration, 3),
#             "model": "mock-llm",
#             "embedding_model": "weaviate-openai",
#             # A/B 실험 메타데이터
#             "prompt_version": prompt_version,
#             "ab_test_group": ab_test_group,
#             "use_rerank": use_rerank,
#             **prompt_metadata,
#         }

#         # 6. Weaviate storage will be handled at API level with actual query_id

#         # Success logging
#         log_rag_operation(
#             query=query,
#             success=True,
#             duration=duration,
#             contexts_count=len(context_texts),
#             user_id=user_id,
#             channel_id=channel_id,
#             request_id=request_id,
#         )

#         # Record pipeline latency metric
#         record_rag_pipeline_latency(duration)

#         logger.info("RAG pipeline completed successfully in {:.3f}s", duration)
#         return answer, context_texts, metadata

#     except RAGException:
#         # RAG-related exceptions are re-raised
#         duration = time.time() - start_time
#         # Record pipeline latency even on handled RAGException
#         record_rag_pipeline_latency(duration)
#         log_rag_operation(
#             query=query,
#             success=False,
#             duration=duration,
#             user_id=user_id,
#             channel_id=channel_id,
#             request_id=request_id,
#         )
#         raise

#     except Exception as e:
#         # Unexpected exception
#         duration = time.time() - start_time
#         logger.error(f"Unexpected error in RAG pipeline: {str(e)}")
#         # Record pipeline latency on unexpected error
#         record_rag_pipeline_latency(duration)
#         log_rag_operation(
#             query=query,
#             success=False,
#             duration=duration,
#             user_id=user_id,
#             channel_id=channel_id,
#             request_id=request_id,
#         )
#         raise RAGException(f"Unexpected error in RAG pipeline: {str(e)}")


def store_rag_result_in_weaviate(
    query: str,
    answer: str,
    contexts: List[str],
    metadata: Dict[str, Any],
    query_id: Optional[str] = None,
):
    """
    Store RAG result in Weaviate for future retrieval (with fallback)
    """
    try:
        # Try to import and use Weaviate client
        try:
            from app.core.weaviate_client import weaviate_client

            # Create a combined document content
            content = f"Query: {query}\n\nAnswer: {answer}\n\nContext:\n" + "\n".join(
                contexts
            )

            # Store in Weaviate
            document_id = weaviate_client.add_document(
                content=content,
                source="rag_result",
                metadata={
                    **metadata,
                    "type": "rag_result",
                    "original_query": query,
                    "answer": answer,
                    "context_count": len(contexts),
                },
                query_id=query_id,
            )

            logger.info("Stored RAG result in Weaviate with ID: {}", document_id)

        except ImportError as e:
            logger.warning(f"Weaviate client not available for storage: {str(e)}")
            logger.info("RAG result not stored in Weaviate (fallback mode)")

    except Exception as e:
        logger.error(f"Failed to store RAG result in Weaviate: {str(e)}")
        # Don't raise exception - this is not critical for the main flow
