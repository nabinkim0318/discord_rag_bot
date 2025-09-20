# # backend/app/services/enhanced_rag_service.py
# """
# Enhanced RAG service
# - Query decomposition and intent detection
# - Multi-route search
# - Discord-optimized response generation
# """

# import time
# from typing import Any, Dict, List, Optional, Tuple

# from rag_agent.generation.discord_prompt_builder import (
#     build_discord_prompt,
#     format_discord_response,
#     parse_discord_response,
# )

# # RAG Agent imports
# from rag_agent.query.query_planner import plan_query
# from rag_agent.retrieval.enhanced_retrieval import enhanced_retrieve

# from app.core.logging import logger
# from app.core.metrics import (
#     record_failure_metric,
#     record_rag_pipeline_latency,
#     record_retrieval_hit,
#     record_retriever_topk,
# )

# # class EnhancedRAGService:
# #     """Enhanced RAG service"""

# #     def __init__(self, db_path: str = "rag_kb.sqlite3", **retrieval_kwargs):
# #         self.db_path = db_path
# #         self.retrieval_kwargs = retrieval_kwargs

# #         # LLM 클라이언트 (기존 구현 재사용)
# #         self.llm_client = self._get_llm_client()

# #     def run_enhanced_rag_pipeline(
# #         self,
# #         query: str,
# #         top_k: int = 5,
# #         *,
# #         user_id: Optional[str] = None,
# #         channel_id: Optional[str] = None,
# #         request_id: Optional[str] = None,
# #     ) -> Tuple[str, List[Dict], Dict[str, Any]]:
# #         """
# #         Run enhanced RAG pipeline

# #         Args:
# #             query: User query
# #             top_k: Top k to search
# #             user_id: User ID
# #             channel_id: Channel ID
# #             request_id: Request ID

# #         Returns:
# #             Tuple[str, List[Dict], Dict[str, Any]]: (answer, context, metadata)
# #         """
# #         start_time = time.time()

# #         try:
# #             # 1. Plan query
# #             logger.info(f"Planning query: {query}")
# #             query_plan = plan_query(query)

# #             # Handle clarification needed
# #             if query_plan.requires_clarification:
# #                 return self._handle_clarification_needed(query_plan)

# #             # 2. Perform enhanced search
# #             logger.info(f"Retrieving for {len(query_plan.intents)} intents")
# #             retrieval_result = enhanced_retrieve(
# #                 query_plan=query_plan,
# #                 db_path=self.db_path,
# #                 k_final=top_k,
# #                 **self.retrieval_kwargs,
# #             )

# #             # 3. Validate context
# #             if not retrieval_result.final_results:
# #                 return self._handle_no_results(query, query_plan)

# #             # 4. Generate prompt
# #             prompt = build_discord_prompt(retrieval_result, query, version="v2.0")

# #             # 5. Call LLM
# #             logger.info("Calling LLM for response generation")
# #             llm_response = self._call_llm(prompt)

# #             # 6. Parse and format response
# #             discord_response = parse_discord_response(llm_response,
#  retrieval_result)
# #             final_answer = format_discord_response(discord_response)

# #             # 7. Collect metadata
# #             metadata = self._collect_metadata(
# #                 query_plan, retrieval_result, discord_response, start_time
# #             )

# #             # 8. Format contexts
# #             contexts = self._format_contexts(retrieval_result.final_results)

# #             # 9. Record metrics
# #             self._record_metrics(retrieval_result, start_time)

# #             logger.info(
# #                 f"Enhanced RAG pipeline completed in {metadata['total_time']:.3f}s"
# #             )

# #             return final_answer, contexts, metadata

# #         except Exception as e:
# #             logger.exception(f"Enhanced RAG pipeline failed: {e}")
# #             record_failure_metric("/api/v1/rag/enhanced", "pipeline_error")
# #             raise

# #     def _handle_clarification_needed(
# #         self, query_plan
# #     ) -> Tuple[str, List[Dict], Dict[str, Any]]:
# #         """Handle clarification needed case"""
# #         answer = "❓ **Additional information needed**\n\n"
# #         answer += f"{query_plan.clarification_question}"

# #         metadata = {
# #             "requires_clarification": True,
# #             "clarification_question": query_plan.clarification_question,
# #             "intents_detected": [intent.intent for intent in query_plan.intents],
# #             "total_time": 0.0,
# #         }

# #         return answer, [], metadata

# #     def _handle_no_results(
# #         self, query: str, query_plan
# #     ) -> Tuple[str, List[Dict], Dict[str, Any]]:
# #         """Handle no search results case"""
# #         answer = "😔 **No search results found**\n\n"
# #         answer += f"Could not find information about '{query}'.\n\n"
# #         answer += "**Try the following:**\n"
# #         answer += "- Ask with different keywords\n"
# #         answer += "- Ask more specific questions\n"
# #         answer += "- Request help in #general channel"

# #         metadata = {
# #             "no_results": True,
# #             "intents_detected": [intent.intent for intent in query_plan.intents],
# #             "total_time": 0.0,
# #         }

# #         return answer, [], metadata

# #     def _call_llm(self, prompt: str) -> str:
# #         """Call LLM (reuse existing implementation)"""
# #         try:
# #             # OpenAI API call (existing implementation)
# #             import openai

# #             response = openai.ChatCompletion.create(
# #                 model="gpt-4o-mini",
# #                 messages=[
# #                     {
# #                         "role": "system",
# #                         "content": "You are a helpful AI assistant for"
# #                         "AI Bootcamp internship.",
# #                     },
# #                     {"role": "user", "content": prompt},
# #                 ],
# #                 max_tokens=1000,
# #                 temperature=0.1,
# #             )

# #             return response.choices[0].message.content

# #         except Exception as e:
# #             logger.exception(f"LLM call failed: {e}")
# #             record_failure_metric("/api/v1/rag/enhanced", "llm_error")
# #             raise

# #     def _get_llm_client(self):
# #         """Initialize LLM client"""
# #         # Reuse existing LLM client
# #         return None

# #     def _collect_metadata(
# #         self, query_plan, retrieval_result, discord_response, start_time: float
# #     ) -> Dict[str, Any]:
# #         """Collect metadata"""
# #         total_time = time.time() - start_time

# #         metadata = {
# #             "total_time": total_time,
# #             "retrieval_time": retrieval_result.retrieval_time,
# #             "generation_time": total_time - retrieval_result.retrieval_time,
# #             "query_plan": {
# #                 "original_query": query_plan.original_query,
# #                 "intents": [intent.intent for intent in query_plan.intents],
# #                 "requires_clarification": query_plan.requires_clarification,
# #             },
# #             "retrieval": {
# #                 "total_results": len(retrieval_result.final_results),
# #                 "results_by_intent": {
# #                     intent: len(results)
# #                     for intent, results
# in retrieval_result.results_by_intent.items()
# #                 },
# #                 "metadata": retrieval_result.metadata,
# #             },
# #             "response": {
# #                 "sections_count": len(discord_response.sections),
# #                 "sources_count": len(discord_response.sources),
# #                 "uncertainty_warnings": len(discord_response.uncertainty_warnings),
# #                 "clarification_needed": discord_response.clarification_needed,
# #             },
# #         }

# #         return metadata

# #     def _format_contexts(self, results) -> List[Dict[str, Any]]:
# #         """Format contexts"""
# #         contexts = []

# #         for result in results:
# #             context = {
# #                 "chunk_uid": result.chunk_uid,
# #                 "content": result.content,
# #                 "source": result.source,
# #                 "score": result.score,
# #                 "intent": result.intent,
# #                 "metadata": result.metadata,
# #             }
# #             contexts.append(context)

# #         return contexts

# #     def _record_metrics(self, retrieval_result, start_time: float):
# #         """Record metrics"""
# #         try:
# #             # Record retrieval hit
# #             record_retrieval_hit(bool(retrieval_result.final_results))

# #             # Record Top-k
# #             record_retriever_topk(len(retrieval_result.final_results))

# #             # Record latency
# #             total_time = time.time() - start_time
# #             record_rag_pipeline_latency(total_time)

# #         except Exception as e:
# #             logger.exception(f"Metrics recording failed: {e}")


# # # Global instance
# # enhanced_rag_service = None


# # def get_enhanced_rag_service(**kwargs) -> EnhancedRAGService:
# #     """Return enhanced RAG service instance"""
# #     global enhanced_rag_service
# #     if enhanced_rag_service is None:
# #         enhanced_rag_service = EnhancedRAGService(**kwargs)
# #     return enhanced_rag_service


# # def run_enhanced_rag_pipeline(
# #     query: str, top_k: int = 5, **kwargs
# # ) -> Tuple[str, List[Dict], Dict[str, Any]]:
# #     """Run enhanced RAG pipeline (convenience function)"""
# #     service = get_enhanced_rag_service()
# #     return service.run_enhanced_rag_pipeline(query, top_k, **kwargs)
