# rag_agent/retrieval/enhanced_retrieval.py
"""
Enhanced hybrid search system
- Intent-based filtering
- Multi-route search
- Re-ranking and deduplication
- Section-based response assembly
"""

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from rag_agent.query.query_planner import QueryIntent, QueryPlan

# from rag_agent.retrieval.fuse import mmr_select, rrf_combine
from rag_agent.retrieval.retrieval_pipeline import search_hybrid


@dataclass
class RetrievalResult:
    """Search result"""

    chunk_uid: str
    content: str
    source: str
    doc_id: Optional[str] = None
    chunk_id: Optional[int] = None
    page: Optional[int] = None
    score: float = 0.0
    intent: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EnhancedRetrievalResult:
    """Enhanced search result"""

    original_query: str
    query_plan: QueryPlan
    results_by_intent: Dict[str, List[RetrievalResult]]
    final_results: List[RetrievalResult]
    retrieval_time: float
    metadata: Dict[str, Any]


class EnhancedRetriever:
    """Enhanced retriever"""

    def __init__(
        self,
        db_path: str,
        k_bm25: int = 30,
        k_vec: int = 30,
        k_final: int = 8,
        bm25_weight: float = 0.4,
        vec_weight: float = 0.6,
        mmr_lambda: float = 0.65,
    ):
        self.db_path = db_path
        self.k_bm25 = k_bm25
        self.k_vec = k_vec
        self.k_final = k_final
        self.bm25_weight = bm25_weight
        self.vec_weight = vec_weight
        self.mmr_lambda = mmr_lambda

    def retrieve(self, query_plan: QueryPlan) -> EnhancedRetrievalResult:
        """
        Perform enhanced search based on query plan

        Args:
            query_plan: Query plan

        Returns:
            EnhancedRetrievalResult: Search results
        """
        start_time = time.time()

        # 1. Perform search by intent
        results_by_intent = {}
        for intent in query_plan.intents:
            intent_results = self._retrieve_for_intent(intent)
            results_by_intent[intent.intent] = intent_results

        # 2. Merge results and re-rank
        final_results = self._merge_and_rerank(results_by_intent, query_plan)

        # 3. Collect metadata
        metadata = self._collect_metadata(query_plan, results_by_intent, final_results)

        retrieval_time = time.time() - start_time

        return EnhancedRetrievalResult(
            original_query=query_plan.original_query,
            query_plan=query_plan,
            results_by_intent=results_by_intent,
            final_results=final_results,
            retrieval_time=retrieval_time,
            metadata=metadata,
        )

    def _retrieve_for_intent(self, intent: QueryIntent) -> List[RetrievalResult]:
        """Perform search for specific intent"""
        # Convert filters
        sqlite_filters = self._convert_to_sqlite_filters(intent.filters)
        weaviate_filters = self._convert_to_weaviate_filters(intent.filters)

        # Perform hybrid search
        search_results = search_hybrid(
            query=intent.query,
            db_path=self.db_path,
            k_bm25=self.k_bm25,
            k_vec=self.k_vec,
            top_k_final=self.k_final,
            sqlite_filters=sqlite_filters,
            weaviate_filters=weaviate_filters,
            bm25_weight=self.bm25_weight,
            vec_weight=self.vec_weight,
            mmr_lambda=self.mmr_lambda,
            record_latency=False,
        )

        # Convert results
        results = []
        for item in search_results:
            result = RetrievalResult(
                chunk_uid=item["chunk_uid"],
                content=item["content"],
                source=item.get("source"),
                doc_id=item.get("doc_id"),
                chunk_id=item.get("chunk_id"),
                page=item.get("page"),
                score=item["score"],
                intent=intent.intent,
                metadata=item.get("metadata"),
            )
            results.append(result)

        return results

    def _convert_to_sqlite_filters(
        self, filters: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Convert to SQLite filters"""
        if not filters:
            return None

        sqlite_filters = {}

        # doc_type filter
        if "doc_type" in filters:
            sqlite_filters["doc_type"] = filters["doc_type"]

        # week filter
        if "week" in filters:
            sqlite_filters["week"] = filters["week"]

        # audience filter
        if "audience" in filters:
            sqlite_filters["audience"] = filters["audience"]

        return sqlite_filters if sqlite_filters else None

    def _convert_to_weaviate_filters(
        self, filters: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Convert to Weaviate filters"""
        if not filters:
            return None

        weaviate_filters = []

        # doc_type filter
        if "doc_type" in filters:
            weaviate_filters.append(
                {
                    "path": ["doc_type"],
                    "operator": "Equal",
                    "valueString": filters["doc_type"],
                }
            )

        # week filter
        if "week" in filters:
            weaviate_filters.append(
                {"path": ["week"], "operator": "Equal", "valueInt": filters["week"]}
            )

        # audience filter
        if "audience" in filters:
            weaviate_filters.append(
                {
                    "path": ["audience"],
                    "operator": "Equal",
                    "valueString": filters["audience"],
                }
            )

        if len(weaviate_filters) == 1:
            return weaviate_filters[0]
        elif len(weaviate_filters) > 1:
            return {"operator": "And", "operands": weaviate_filters}

        return None

    def _merge_and_rerank(
        self, results_by_intent: Dict[str, List[RetrievalResult]], query_plan: QueryPlan
    ) -> List[RetrievalResult]:
        """Merge results and re-rank"""
        all_results = []

        # Collect results by intent
        for intent_name, results in results_by_intent.items():
            for result in results:
                all_results.append(result)

        # Remove duplicates
        deduplicated = self._deduplicate_results(all_results)

        # Sort by score
        deduplicated.sort(key=lambda x: x.score, reverse=True)

        # Limit final results
        return deduplicated[: self.k_final]

    def _deduplicate_results(
        self, results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """Remove duplicate results"""
        seen = set()
        deduplicated = []

        for result in results:
            # Duplicate key: (source, chunk_uid)
            key = (result.source, result.chunk_uid)

            if key not in seen:
                seen.add(key)
                deduplicated.append(result)
            else:
                # If duplicate, update with higher score
                for i, existing in enumerate(deduplicated):
                    if (existing.source, existing.chunk_uid) == key:
                        if result.score > existing.score:
                            deduplicated[i] = result
                        break

        return deduplicated

    def _collect_metadata(
        self,
        query_plan: QueryPlan,
        results_by_intent: Dict[str, List[RetrievalResult]],
        final_results: List[RetrievalResult],
    ) -> Dict[str, Any]:
        """Collect metadata"""
        metadata = {
            "total_intents": len(query_plan.intents),
            "intent_names": [intent.intent for intent in query_plan.intents],
            "results_per_intent": {
                intent: len(results) for intent, results in results_by_intent.items()
            },
            "total_results": len(final_results),
            "requires_clarification": query_plan.requires_clarification,
            "clarification_question": query_plan.clarification_question,
        }

        # Score distribution by intent
        intent_scores = {}
        for intent_name, results in results_by_intent.items():
            if results:
                intent_scores[intent_name] = {
                    "max_score": max(r.score for r in results),
                    "avg_score": sum(r.score for r in results) / len(results),
                    "min_score": min(r.score for r in results),
                }

        metadata["intent_scores"] = intent_scores

        return metadata


# Global instance
enhanced_retriever = None


def get_enhanced_retriever(db_path: str, **kwargs) -> EnhancedRetriever:
    """Return enhanced retriever instance"""
    global enhanced_retriever
    if enhanced_retriever is None:
        enhanced_retriever = EnhancedRetriever(db_path, **kwargs)
    return enhanced_retriever


def enhanced_retrieve(
    query_plan: QueryPlan, db_path: str, **kwargs
) -> EnhancedRetrievalResult:
    """Perform enhanced search (convenience function)"""
    retriever = get_enhanced_retriever(db_path, **kwargs)
    return retriever.retrieve(query_plan)
