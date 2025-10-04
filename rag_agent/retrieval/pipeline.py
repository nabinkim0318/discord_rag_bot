"""
Retrieval Pipeline for RAG Agent

This module provides the main retrieval pipeline that orchestrates
search operations including BM25, vector search, and hybrid retrieval.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .enhanced_retrieval import enhanced_retrieve
from .fuse import mmr_select, rrf_combine

# Import existing retrieval functions
from .keyword import bm25_search
from .vector import vector_search

logger = logging.getLogger(__name__)


class RetrievalPipeline:
    """Main retrieval pipeline for document search."""

    def __init__(
        self,
        sqlite_path: str = "rag_kb.sqlite3",
        weaviate_url: Optional[str] = None,
        use_enhanced: bool = False,
    ):
        """
        Initialize the retrieval pipeline.

        Args:
            sqlite_path: Path to SQLite database for BM25 search
            weaviate_url: URL for Weaviate vector database
            use_enhanced: Whether to use enhanced retrieval
        """
        self.sqlite_path = sqlite_path
        self.weaviate_url = weaviate_url
        self.use_enhanced = use_enhanced

    def search(
        self,
        query: str,
        k_bm25: int = 30,
        k_vec: int = 30,
        k_final: int = 8,
        bm25_weight: float = 0.4,
        vec_weight: float = 0.6,
        mmr_lambda: float = 0.65,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining BM25 and vector search.

        Args:
            query: Search query
            k_bm25: Number of BM25 results
            k_vec: Number of vector search results
            k_final: Final number of results after MMR
            bm25_weight: Weight for BM25 results in RRF
            vec_weight: Weight for vector results in RRF
            mmr_lambda: Lambda parameter for MMR diversity

        Returns:
            List of search results with metadata
        """
        try:
            if self.use_enhanced:
                return self._enhanced_search(query, k_final, **kwargs)
            else:
                return self._hybrid_search(
                    query,
                    k_bm25,
                    k_vec,
                    k_final,
                    bm25_weight,
                    vec_weight,
                    mmr_lambda,
                    **kwargs,
                )
        except Exception as e:
            logger.error(f"Error in retrieval pipeline: {e}")
            raise

    def _hybrid_search(
        self,
        query: str,
        k_bm25: int,
        k_vec: int,
        k_final: int,
        bm25_weight: float,
        vec_weight: float,
        mmr_lambda: float,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Perform traditional hybrid search."""

        # 1. BM25 search
        bm25_results = []
        if self.sqlite_path and Path(self.sqlite_path).exists():
            try:
                bm25_results = bm25_search(query, self.sqlite_path, k_bm25)
                logger.info(f"BM25 search returned {len(bm25_results)} results")
            except Exception as e:
                logger.warning(f"BM25 search failed: {e}")

        # 2. Vector search
        vector_results = []
        if self.weaviate_url:
            try:
                vector_results = vector_search(query, self.weaviate_url, k_vec)
                logger.info(f"Vector search returned {len(vector_results)} results")
            except Exception as e:
                logger.warning(f"Vector search failed: {e}")

        # 3. Combine results using RRF
        if bm25_results and vector_results:
            combined_results = rrf_combine(
                bm25_results, vector_results, weight1=bm25_weight, weight2=vec_weight
            )
        elif bm25_results:
            combined_results = bm25_results
        elif vector_results:
            combined_results = vector_results
        else:
            logger.warning("No search results available")
            return []

        # 4. Apply MMR for diversity
        if len(combined_results) > k_final:
            final_results = mmr_select(combined_results, k_final, mmr_lambda)
        else:
            final_results = combined_results

        logger.info(f"Final retrieval returned {len(final_results)} results")
        return final_results

    def _enhanced_search(
        self, query: str, k_final: int, **kwargs
    ) -> List[Dict[str, Any]]:
        """Perform enhanced search using advanced retrieval."""
        try:
            results = enhanced_retrieve(
                query=query,
                sqlite_path=self.sqlite_path,
                weaviate_url=self.weaviate_url,
                k_final=k_final,
                **kwargs,
            )
            logger.info(f"Enhanced search returned {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Enhanced search failed: {e}")
            # Fallback to basic hybrid search
            return self._hybrid_search(query, 30, 30, k_final, 0.4, 0.6, 0.65, **kwargs)

    def bm25_only(self, query: str, k: int = 30) -> List[Dict[str, Any]]:
        """Perform BM25 search only."""
        if not self.sqlite_path or not Path(self.sqlite_path).exists():
            logger.warning("SQLite database not available for BM25 search")
            return []

        try:
            return bm25_search(query, self.sqlite_path, k)
        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            return []

    def vector_only(self, query: str, k: int = 30) -> List[Dict[str, Any]]:
        """Perform vector search only."""
        if not self.weaviate_url:
            logger.warning("Weaviate URL not configured for vector search")
            return []

        try:
            return vector_search(query, self.weaviate_url, k)
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []


def create_retrieval_pipeline(
    sqlite_path: str = "rag_kb.sqlite3",
    weaviate_url: Optional[str] = None,
    use_enhanced: bool = False,
) -> RetrievalPipeline:
    """
    Create a retrieval pipeline instance.

    Args:
        sqlite_path: Path to SQLite database
        weaviate_url: URL for Weaviate database
        use_enhanced: Whether to use enhanced retrieval

    Returns:
        RetrievalPipeline instance
    """
    return RetrievalPipeline(
        sqlite_path=sqlite_path, weaviate_url=weaviate_url, use_enhanced=use_enhanced
    )


def quick_search(
    query: str,
    sqlite_path: str = "rag_kb.sqlite3",
    weaviate_url: Optional[str] = None,
    k: int = 10,
    **kwargs,
) -> List[Dict[str, Any]]:
    """
    Quick search function for simple use cases.

    Args:
        query: Search query
        sqlite_path: Path to SQLite database
        weaviate_url: URL for Weaviate database
        k: Number of results to return
        **kwargs: Additional search parameters

    Returns:
        List of search results
    """
    pipeline = create_retrieval_pipeline(sqlite_path, weaviate_url)
    return pipeline.search(query, k_final=k, **kwargs)


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <query> [k]")
        sys.exit(1)

    query = sys.argv[1]
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    try:
        results = quick_search(query, k=k)
        print(f"Found {len(results)} results for query: '{query}'")
        for i, result in enumerate(results[:5]):  # Show top 5
            print(f"{i + 1}. {result.get('text', '')[:100]}...")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
