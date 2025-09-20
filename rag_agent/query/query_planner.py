# rag_agent/query/query_planner.py
"""
Query decomposition and intent detection system
Analyze user queries and decompose them into intent-based sub-queries
and generate appropriate filters.
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class QueryIntent:
    """Query intent information"""

    intent: str  # schedule, faq, resources
    query: str  # original or refined query
    confidence: float  # 0.0 ~ 1.0
    filters: Dict[str, Any]  # Weaviate filter conditions
    extracted_info: Dict[str, Any]  # 추출된 정보 (week, topic 등)


@dataclass
class QueryPlan:
    """Query plan"""

    original_query: str
    intents: List[QueryIntent]
    requires_clarification: bool = False
    clarification_question: Optional[str] = None


class QueryPlanner:
    """Query plan generator"""

    def __init__(self):
        # Intent-based keyword mapping
        self.intent_keywords = {
            "schedule": {
                "keywords": [
                    "week",
                    "week",
                    "when",
                    "schedule",
                    "pitch",
                    "demo",
                    "matching",
                    "deadline",
                    "time",
                    "date",
                ],
                "patterns": [r"week\s*(\d+)", r"week\s*(\d+)", r"(\d+)\s*week"],
            },
            "faq": {
                "keywords": [
                    "paid",
                    "unpaid",
                    "visa",
                    "opt",
                    "cpt",
                    "regulation",
                    "policy",
                    "requirement",
                    "commit",
                    "time",
                ],
                "patterns": [],
            },
            "resources": {
                "keywords": [
                    "link",
                    "material",
                    "playlist",
                    "video",
                    "training",
                    "training",
                    "course",
                    "lecture",
                    "form",
                    "form",
                ],
                "patterns": [],
            },
        }

        # Split separator
        self.split_patterns = [
            r"\s+그리고\s+",
            r"\s+랑\s+",
            r"\s+및\s+",
            r"\s+,\s+",
            r"\s+;\s+",
        ]

    def plan_query(self, user_query: str) -> QueryPlan:
        """
        Analyze user query and plan

        Args:
            user_query: user query

        Returns:
            QueryPlan: query plan
        """
        original_query = user_query.strip()

        # 1. Query decomposition (compound query processing)
        sub_queries = self._split_query(original_query)

        # 2. Intent analysis for each sub-query
        intents = []
        for sub_query in sub_queries:
            intent = self._analyze_intent(sub_query)
            if intent:
                intents.append(intent)

        # 3. Check if clarification is needed
        requires_clarification, clarification_question = (
            self._check_clarification_needed(original_query, intents)
        )

        return QueryPlan(
            original_query=original_query,
            intents=intents,
            requires_clarification=requires_clarification,
            clarification_question=clarification_question,
        )

    def _split_query(self, query: str) -> List[str]:
        """Compound query to sub-queries"""
        # 분할 구분자로 나누기
        parts = [query]
        for pattern in self.split_patterns:
            new_parts = []
            for part in parts:
                new_parts.extend(re.split(pattern, part, flags=re.IGNORECASE))
            parts = new_parts

        # Remove empty strings and refine
        sub_queries = [q.strip() for q in parts if q.strip()]

        # If not split, return original
        return sub_queries if len(sub_queries) > 1 else [query]

    def _analyze_intent(self, query: str) -> Optional[QueryIntent]:
        """Intent analysis for sub-query"""
        query_lower = query.lower()
        intent_scores = {}

        # Calculate score for each intent
        for intent, config in self.intent_keywords.items():
            score = 0.0

            # Keyword matching
            keyword_matches = sum(1 for kw in config["keywords"] if kw in query_lower)
            if keyword_matches > 0:
                score += keyword_matches * 0.3

            # Pattern matching
            for pattern in config["patterns"]:
                if re.search(pattern, query_lower):
                    score += 0.4

            intent_scores[intent] = score

        # Select the intent with the highest score
        if not intent_scores or max(intent_scores.values()) < 0.3:
            return None

        best_intent = max(intent_scores, key=intent_scores.get)
        confidence = min(intent_scores[best_intent], 1.0)

        # Generate filters and extracted information
        filters, extracted_info = self._generate_filters_and_info(best_intent, query)

        return QueryIntent(
            intent=best_intent,
            query=query,
            confidence=confidence,
            filters=filters,
            extracted_info=extracted_info,
        )

    def _generate_filters_and_info(
        self, intent: str, query: str
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Generate filters and extracted information based on intent"""
        filters = {}
        extracted_info = {}

        if intent == "schedule":
            # Extract week information
            week = self._extract_week(query)
            if week:
                filters["week"] = week
                extracted_info["week"] = week

            # Schedule related filters
            filters["doc_type"] = "schedule"

        elif intent == "faq":
            # FAQ related filters
            filters["doc_type"] = "faq"

        elif intent == "resources":
            # Resources related filters
            filters["doc_type"] = "resources"

            # Extract audience (engineer, pm, designer, all)
            audience = self._extract_audience(query)
            if audience:
                filters["audience"] = audience
                extracted_info["audience"] = audience

        return filters, extracted_info

    def _extract_week(self, query: str) -> Optional[int]:
        """Extract week information from query"""
        patterns = [r"week\s*(\d+)", r"주차\s*(\d+)", r"(\d+)\s*주차", r"(\d+)\s*week"]

        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue

        return None

    def _extract_audience(self, query: str) -> Optional[str]:
        """Extract audience information from query"""
        query_lower = query.lower()

        if any(
            kw in query_lower
            for kw in ["engineer", "engineer", "development", "coding"]
        ):
            return "engineer"
        elif any(kw in query_lower for kw in ["pm", "product", "product", "planning"]):
            return "pm"
        elif any(kw in query_lower for kw in ["designer", "design", "ui", "ux"]):
            return "designer"

        return "all"

    def _check_clarification_needed(
        self, original_query: str, intents: List[QueryIntent]
    ) -> tuple[bool, Optional[str]]:
        """Check if clarification is needed"""
        # Week information is needed but not provided
        schedule_intents = [i for i in intents if i.intent == "schedule"]
        if schedule_intents and not any(
            i.extracted_info.get("week") for i in schedule_intents
        ):
            return True, "Which week are you referring to? (e.g. Week 4)"

        # Too many intents
        if len(intents) > 3:
            return True, "The question is too complex. Please ask one at a time?"

        return False, None


# Global instance
query_planner = QueryPlanner()


def plan_query(user_query: str) -> QueryPlan:
    """Query planning (convenience function)"""
    return query_planner.plan_query(user_query)
