# rag_agent/generation/discord_prompt_builder.py
"""
Discord-optimized prompt builder v2.0
- Section-based response structure
- Link standardization
- Uncertainty notation
- Discord UI-friendly formatting
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    from rag_agent.retrieval.enhanced_retrieval import (
        EnhancedRetrievalResult,  # type: ignore
    )
except Exception:
    EnhancedRetrievalResult = object

LINK_RE = re.compile(r"<([^>|]+)\|([^>]+)>|https?://\S+")


def _extract_links(text: str) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for m in LINK_RE.finditer(text):
        if m.group(2):  # <title|url>
            out.append({"title": m.group(1), "url": m.group(2), "type": "link"})
        else:
            url = m.group(0)
            out.append({"title": url, "url": url, "type": "link"})
    return out


@dataclass
class DiscordResponse:
    """Discord-optimized response"""

    summary: str
    sections: List[Dict[str, Any]]
    sources: List[Dict[str, str]]
    uncertainty_warnings: List[str]
    clarification_needed: bool = False
    clarification_question: Optional[str] = None


class DiscordPromptBuilder:
    """Discord-optimized prompt builder"""

    def __init__(self):
        self.system_prompt = self._get_system_prompt()
        self.response_template = self._get_response_template()

    def build_prompt(
        self,
        retrieval_result: EnhancedRetrievalResult,
        user_query: str,
        version: str = "v2.0",
    ) -> str:
        """
        Generate Discord-optimized prompt

        Args:
            retrieval_result: Search results
            user_query: User query
            version: Prompt version

        Returns:
            str: Complete prompt
        """
        # Build context
        context_sections = self._build_context_sections(retrieval_result)

        # Assemble prompt
        prompt = f"""{self.system_prompt}

## User Question
{user_query}

## Retrieved Context
{context_sections}

## Response Guidelines
{self.response_template}
Based on the above context, provide accurate and helpful answers
to user questions.
Speculation outside the context is prohibited, and
uncertain content should be clearly stated.
Links should be formatted as <title|URL>.
"""

        return prompt

    def _get_system_prompt(self) -> str:
        """System prompt"""
        return """You are a helpful assistant for AI Bootcamp
    internship related questions.

## Core Principles
1. **Accuracy First**: Answer only within the provided context
2. **Uncertainty Notation**: Clearly state "not specified in documents"
    for unknown content
3. **Practicality**: Provide information that users can act on immediately
4. **Responsibility**: Recommend consulting official channels for policy/legal matters

## Response Structure
- **Summary**: 1-2 line core answer
- **Details**: Intent-based sections (schedule/policy/resources)
- **Sources**: Related links and documents
- **Cautions**: Uncertainty or additional guidance"""

    def _get_response_template(self) -> str:
        """Response template"""
        return """Please respond in the following format:

**Summary:** [1-2 line core answer]

**Schedule:** (if applicable)
- [Specific date/time/week]
- [Related link: <title|URL>]

**Policy:** (if applicable)
- [Policy content summary]
- [Caution: Recommend consulting official channels]

**Resources:** (if applicable)
- [Material name: <title|URL>]
- [Additional explanation]

**Sources:**
- [Document name] - [Section name]
- [Related link: <title|URL>]

**Caution:** (if there is uncertain content)
- [Uncertainty notation and additional guidance]"""

    def _build_context_sections(self, retrieval_result: EnhancedRetrievalResult) -> str:
        """Build context sections"""
        context_parts = []

        # Build context by intent
        for intent_name, results in retrieval_result.results_by_intent.items():
            if not results:
                continue

            intent_section = f"### {intent_name.upper()} Related Information\n"

            for i, result in enumerate(results[:3], 1):  # Top 3 only
                intent_section += f"""
**{i}. {result.source}**
{result.content[:300]}{"..." if len(result.content) > 300 else ""}
Score: {result.score:.3f}
"""

            context_parts.append(intent_section)

        # Final results context
        if retrieval_result.final_results:
            final_section = "### Integrated Search Results\n"
            for i, result in enumerate(retrieval_result.final_results[:5], 1):
                final_section += f"""
**{i}. {result.source}** (Intent: {result.intent})
{result.content[:200]}{"..." if len(result.content) > 200 else ""}
Score: {result.score:.3f}
"""
            context_parts.append(final_section)

        return "\n".join(context_parts)

    def parse_response(
        self, llm_response: str, retrieval_result: EnhancedRetrievalResult
    ) -> DiscordResponse:
        """
        Parse LLM response into Discord format

        Args:
            llm_response: LLM response
            retrieval_result: Search results

        Returns:
            DiscordResponse: Parsed response
        """
        # Parse by sections
        sections = self._parse_sections(llm_response)

        # Extract summary
        summary = self._extract_summary(llm_response)

        # Extract sources
        sources = self._extract_sources(llm_response, retrieval_result)

        # Extract uncertainty warnings
        uncertainty_warnings = self._extract_uncertainty_warnings(llm_response)

        return DiscordResponse(
            summary=summary,
            sections=sections,
            sources=sources,
            uncertainty_warnings=uncertainty_warnings,
            clarification_needed=retrieval_result.query_plan.requires_clarification,
            clarification_question=retrieval_result.query_plan.clarification_question,
        )

    def _parse_sections(self, response: str) -> List[Dict[str, Any]]:
        """Parse sections from response"""
        sections = []

        # Section-specific regex patterns
        section_patterns = {
            "schedule": r"\*\*Schedule:\*\*\s*(.*?)(?=\*\*|$)",
            "policy": r"\*\*Policy:\*\*\s*(.*?)(?=\*\*|$)",
            "resources": r"\*\*Resources:\*\*\s*(.*?)(?=\*\*|$)",
            "caution": r"\*\*Caution:\*\*\s*(.*?)(?=\*\*|$)",
        }

        for section_name, pattern in section_patterns.items():
            match = re.search(pattern, response, re.DOTALL)
            if match:
                content = match.group(1).strip()
                if content:
                    sections.append(
                        {"name": section_name, "content": content, "type": section_name}
                    )

        return sections

    def _extract_summary(self, response: str) -> str:
        """Extract summary"""
        summary_match = re.search(
            r"\*\*Summary:\*\*\s*(.*?)(?=\*\*|$)", response, re.DOTALL
        )
        if summary_match:
            return summary_match.group(1).strip()

        # If no summary, use first paragraph
        first_paragraph = response.split("\n\n")[0]
        return first_paragraph.strip()

    def _extract_sources(
        self, response: str, retrieval_result: EnhancedRetrievalResult
    ) -> List[Dict[str, str]]:
        """Extract sources"""
        sources: List[Dict[str, str]] = []

        # new link extractor
        sources.extend(_extract_links(response))

        # Add sources from search results
        seen_sources = set()
        for result in getattr(retrieval_result, "final_results", []) or []:
            source_key = (
                getattr(result, "source", None),
                getattr(result, "doc_id", None),
            )
            if source_key not in seen_sources:
                seen_sources.add(source_key)
                sources.append(
                    {
                        "title": getattr(result, "source", "document"),
                        "url": f"#{getattr(result, 'chunk_uid', '')}",
                        "type": "document",
                    }
                )

        return sources

    def _extract_uncertainty_warnings(self, response: str) -> List[str]:
        """Extract uncertainty warnings"""
        warnings = []

        # Uncertainty keyword patterns
        uncertainty_patterns = [
            r"not\s+specified\s+in\s+documents",
            r"not\s+certain",
            r"consult\s+official\s+channels",
            r"subject\s+to\s+change",
            r"additional\s+confirmation\s+needed",
        ]

        for pattern in uncertainty_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            warnings.extend(matches)

        return warnings

    def format_for_discord(self, discord_response: DiscordResponse) -> str:
        """Final formatting for Discord"""
        lines = []

        # Summary
        if discord_response.summary:
            lines.append(f"**{discord_response.summary}**")
            lines.append("")

        # Section content
        for section in discord_response.sections:
            lines.append(f"**{section['name']}:**")

            # Convert section content to bullet points
            content_lines = section["content"].split("\n")
            for line in content_lines:
                line = line.strip()
                if line and not line.startswith("-"):
                    lines.append(f"- {line}")
                elif line:
                    lines.append(line)

            lines.append("")

        # Sources
        if discord_response.sources:
            lines.append("**Sources:**")
            for source in discord_response.sources[:3]:  # Maximum 3
                if source["type"] == "link":
                    lines.append(f"- [{source['title']}]({source['url']})")
                else:
                    lines.append(f"- {source['title']}")
            lines.append("")

        # Uncertainty warnings
        if discord_response.uncertainty_warnings:
            lines.append("**⚠️ Caution:**")
            for warning in discord_response.uncertainty_warnings:
                lines.append(f"- {warning}")
            lines.append("")

        # Clarification request
        if (
            discord_response.clarification_needed
            and discord_response.clarification_question
        ):
            lines.append(
                f"**❓ Additional information needed:** "
                f"{discord_response.clarification_question}"
            )

        return "\n".join(lines)


# Global instance
discord_prompt_builder = DiscordPromptBuilder()


def build_discord_prompt(
    retrieval_result: EnhancedRetrievalResult, user_query: str, version: str = "v2.0"
) -> str:
    """Build Discord prompt (convenience function)"""
    return discord_prompt_builder.build_prompt(retrieval_result, user_query, version)


def parse_discord_response(
    llm_response: str, retrieval_result: EnhancedRetrievalResult
) -> DiscordResponse:
    """Parse Discord response (convenience function)"""
    return discord_prompt_builder.parse_response(llm_response, retrieval_result)


def format_discord_response(discord_response: DiscordResponse) -> str:
    """Format Discord response (convenience function)"""
    return discord_prompt_builder.format_for_discord(discord_response)
