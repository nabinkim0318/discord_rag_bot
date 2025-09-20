# rag_agent/query/query_planner.py
"""
Query decomposition and intent detection system (English-only)
- Decomposes compound queries
- Detects intent: schedule | faq | resources
- Extracts light structure (week number, audience)
- Emits lightweight filters to be consumed by retrieval layer
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class QueryIntent:
    """Intent for a (sub-)query."""

    intent: str  # 'schedule' | 'faq' | 'resources'
    query: str  # original or refined sub-query
    confidence: float  # 0.0 ~ 1.0
    filters: Dict[str, Any]  # normalized filters (week, doc_type, audience)
    extracted_info: Dict[str, Any]  # e.g., {"week": 3, "audience": "engineer"}


@dataclass
class QueryPlan:
    """Plan produced for a user query."""

    original_query: str
    intents: List[QueryIntent]
    requires_clarification: bool = False
    clarification_question: Optional[str] = None


class QueryPlanner:
    """English-only query planner with simple keyword/pattern scoring."""

    def __init__(self):
        # NOTE: keyword lists are de-duplicated at init-time
        self.intent_keywords: Dict[str, Dict[str, Any]] = {
            "schedule": {
                "keywords": list(
                    {
                        "week",
                        "when",
                        "schedule",
                        "pitch",
                        "demo",
                        "matching",
                        "deadline",
                        "time",
                        "date",
                    }
                ),
                # capture "week 3", "wk3", "w#3", "3rd week"
                "patterns": [
                    r"\bweek\s*#?\s*(\d{1,2})\b",
                    r"\b(?:wk|w)\s*#?\s*(\d{1,2})\b",
                    r"\b(\d{1,2})(?:st|nd|rd|th)?\s*week\b",
                ],
            },
            "faq": {
                "keywords": list(
                    {
                        "paid",
                        "unpaid",
                        "visa",
                        "opt",
                        "cpt",
                        "regulation",
                        "policy",
                        "requirement",
                        "commitment",
                        "hours",
                    }
                ),
                "patterns": [],
            },
            "resources": {
                "keywords": list(
                    {
                        "link",
                        "material",
                        "playlist",
                        "video",
                        "training",
                        "course",
                        "lecture",
                        "form",
                        "docs",
                        "document",
                        "tutorial",
                    }
                ),
                "patterns": [],
            },
        }

        # Conservative splitters for compound queries.
        # We split on commas/semicolons and " and " only if surrounded by spaces.
        self.split_patterns: List[str] = [
            r"\s*,\s*",
            r"\s*;\s*",
            r"\s+\band\b\s+",
            r"\s+\&\s+",
            r"\s+\bplus\b\s+",
        ]

        # Scoring config
        self.keyword_weight = 0.3
        self.pattern_weight = 0.5
        self.min_intent_threshold = 0.35  # if below, treat as "no clear intent"

    # -------- public --------

    def plan_query(self, user_query: str) -> QueryPlan:
        original_query = (user_query or "").strip()
        sub_queries = self._split_query(original_query)

        intents: List[QueryIntent] = []
        for sub in sub_queries:
            qi = self._analyze_intent(sub)
            if qi:
                intents.append(qi)

        requires, question = self._check_clarification_needed(original_query, intents)

        return QueryPlan(
            original_query=original_query,
            intents=intents,
            requires_clarification=requires,
            clarification_question=question,
        )

    # -------- internals --------

    def _split_query(self, query: str) -> List[str]:
        parts = [query]
        for pattern in self.split_patterns:
            next_parts: List[str] = []
            for p in parts:
                next_parts.extend(re.split(pattern, p, flags=re.IGNORECASE))
            parts = next_parts

        sub_queries = [p.strip() for p in parts if p and p.strip()]
        return sub_queries if len(sub_queries) > 1 else [query]

    def _analyze_intent(self, query: str) -> Optional[QueryIntent]:
        ql = query.lower()
        intent_scores: Dict[str, float] = {}

        for intent, cfg in self.intent_keywords.items():
            score = 0.0

            # Keyword hits (deduped)
            kw_hits = sum(1 for kw in cfg["keywords"] if kw in ql)
            if kw_hits:
                score += kw_hits * self.keyword_weight

            # Regex pattern hits
            for pat in cfg["patterns"]:
                if re.search(pat, ql):
                    score += self.pattern_weight

            # Cap at 1.0
            score = min(score, 1.0)
            intent_scores[intent] = score

        if not intent_scores:
            return None

        best_intent = max(intent_scores, key=intent_scores.get)
        best_score = intent_scores[best_intent]

        if best_score < self.min_intent_threshold:
            return None

        filters, extracted = self._generate_filters_and_info(best_intent, query)

        return QueryIntent(
            intent=best_intent,
            query=query,
            confidence=best_score,
            filters=filters,
            extracted_info=extracted,
        )

    def _generate_filters_and_info(
        self, intent: str, query: str
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        filters: Dict[str, Any] = {}
        extracted: Dict[str, Any] = {}

        if intent == "schedule":
            week = self._extract_week(query)
            if week is not None:
                filters["week"] = week
                extracted["week"] = week
            filters["doc_type"] = "schedule"

        elif intent == "faq":
            filters["doc_type"] = "faq"

        elif intent == "resources":
            filters["doc_type"] = "resources"
            aud = self._extract_audience(query)
            if aud:
                filters["audience"] = aud
                extracted["audience"] = aud

        return filters, extracted

    def _extract_week(self, query: str) -> Optional[int]:
        """
        English-focused week extraction:
        - 'week 3', 'wk3', 'w#3', '3rd week'
        """
        ql = query.lower()
        patterns = [
            r"\bweek\s*#?\s*(\d{1,2})\b",
            r"\b(?:wk|w)\s*#?\s*(\d{1,2})\b",
            r"\b(\d{1,2})(?:st|nd|rd|th)?\s*week\b",
        ]
        for pat in patterns:
            m = re.search(pat, ql)
            if m:
                try:
                    val = int(m.group(1))
                    if 1 <= val <= 20:  # sane guardrail
                        return val
                except ValueError:
                    continue
        return None

    def _extract_audience(self, query: str) -> Optional[str]:
        ql = query.lower()
        if any(k in ql for k in ["engineer", "developer", "dev", "coding"]):
            return "engineer"
        if any(k in ql for k in ["pm", "product manager", "product", "planning"]):
            return "pm"
        if any(k in ql for k in ["designer", "design", "ui", "ux"]):
            return "designer"
        return "all"

    def _check_clarification_needed(
        self, original_query: str, intents: List[QueryIntent]
    ) -> tuple[bool, Optional[str]]:
        # If there is a schedule intent but no week extracted, ask once.
        schedule_intents = [i for i in intents if i.intent == "schedule"]
        if schedule_intents and not any(
            i.extracted_info.get("week") for i in schedule_intents
        ):
            return True, "Which week are you referring to? (e.g., Week 3)"

        # If too many intents, ask to narrow.
        if len(intents) > 3:
            return (
                True,
                "Your question spans multiple topics. Could you ask one at a time?",
            )

        return False, None


# Global instance
query_planner = QueryPlanner()


def plan_query(user_query: str) -> QueryPlan:
    """Query planning (convenience function)"""
    return query_planner.plan_query(user_query)
