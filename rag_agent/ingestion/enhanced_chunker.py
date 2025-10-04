# rag_agent/ingestion/enhanced_chunker.py
"""
Enhanced chunking system
- FAQ 1 question 1 answer unit chunking
- Heading boundary based splitting
- Enhanced metadata (doc_type, week, audience, links)
- Summary and keyword extraction
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ChunkMetadata:
    """Chunk metadata"""

    doc_type: str  # faq, schedule, process, resources
    week: Optional[int] = None
    topic: Optional[str] = None
    audience: str = "all"  # engineer, pm, designer, all
    links: List[str] = None
    anchor_heading: Optional[str] = None
    summary: Optional[str] = None
    keywords: List[str] = None
    updated_at: Optional[str] = None


@dataclass
class EnhancedChunk:
    """Enhanced chunk"""

    content: str
    chunk_id: str
    chunk_uid: str
    source: str
    page: Optional[int] = None
    metadata: ChunkMetadata = None


class EnhancedChunker:
    """Enhanced chunker"""

    def __init__(
        self, chunk_size: int = 600, overlap_size: int = 130, min_chunk_size: int = 100
    ):
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
        self.min_chunk_size = min_chunk_size

        # Document type detection pattern
        self.doc_type_patterns = {
            "faq": [r"FAQ", r"Q\s*&\s*A", r"자주\s*묻는\s*질문", r"질문\s*답변"],
            "schedule": [r"일정", r"스케줄", r"주차", r"week", r"타임라인", r"마감"],
            "process": [r"프로세스", r"절차", r"가이드", r"방법", r"절차"],
            "resources": [r"리소스", r"자료", r"링크", r"훈련", r"트레이닝", r"코스"],
        }

        # Heading pattern
        self.heading_patterns = [
            r"^#{1,6}\s+(.+)$",  # Markdown heading
            r"^(.+)\n={3,}$",  # Underline heading
            r"^(.+)\n-{3,}$",  # Underline heading (dash)
            r"^(\d+\.?\s*.+)$",  # Number list
            r"^([A-Z][A-Z\s]+)$",  # Capital heading
        ]

        # Link pattern
        self.link_patterns = [
            r"\[([^\]]+)\]\(([^)]+)\)",  # Markdown link
            r"(https?://[^\s]+)",  # URL
            r"<([^|]+)\|([^>]+)>",  # <title|url> format
        ]

    def chunk_document(
        self, content: str, source: str, page: Optional[int] = None
    ) -> List[EnhancedChunk]:
        """
        Split document into enhanced chunks

        Args:
            content: Document content
            source: Document source
            page: Page number

        Returns:
            List[EnhancedChunk]: Chunk list
        """
        # 1. Document type detection
        doc_type = self._detect_doc_type(content)

        # 2. Heading structure analysis
        sections = self._split_by_headings(content)

        # 3. Chunking by section
        chunks = []
        for section in sections:
            section_chunks = self._chunk_section(section, source, page, doc_type)
            chunks.extend(section_chunks)

        return chunks

    def _detect_doc_type(self, content: str) -> str:
        """Document type detection"""
        content_lower = content.lower()

        for doc_type, patterns in self.doc_type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    return doc_type

        return "general"

    def _split_by_headings(self, content: str) -> List[Dict[str, Any]]:
        """Split document by heading"""
        lines = content.split("\n")
        sections = []
        current_section = {"heading": None, "content": [], "level": 0}

        for line in lines:
            # Heading detection
            heading_match = None
            for pattern in self.heading_patterns:
                match = re.match(pattern, line.strip())
                if match:
                    heading_match = match
                    break

            if heading_match:
                # Save previous section
                if current_section["content"]:
                    sections.append(current_section)

                # Start new section
                current_section = {
                    "heading": heading_match.group(1).strip(),
                    "content": [line],
                    "level": self._get_heading_level(line),
                }
            else:
                current_section["content"].append(line)

        # Save last section
        if current_section["content"]:
            sections.append(current_section)

        return sections

    def _get_heading_level(self, line: str) -> int:
        """Extract heading level"""
        if line.startswith("#"):
            return len(line) - len(line.lstrip("#"))
        elif line.endswith("=") or line.endswith("-"):
            return 1
        else:
            return 0

    def _chunk_section(
        self, section: Dict[str, Any], source: str, page: Optional[int], doc_type: str
    ) -> List[EnhancedChunk]:
        """Split section into chunks"""
        content = "\n".join(section["content"])
        heading = section["heading"]

        # FAQ special processing
        if doc_type == "faq":
            return self._chunk_faq_section(content, source, page, heading)

        # General chunking
        return self._chunk_general_section(content, source, page, heading, doc_type)

    def _chunk_faq_section(
        self, content: str, source: str, page: Optional[int], heading: Optional[str]
    ) -> List[EnhancedChunk]:
        """FAQ section to Q&A unit chunking"""
        chunks = []

        # Q&A pattern to split
        qa_patterns = [
            r"Q\s*:\s*(.+?)\s*A\s*:\s*(.+?)(?=Q\s*:|$)",
            r"질문\s*:\s*(.+?)\s*답변\s*:\s*(.+?)(?=질문\s*:|$)",  # Q&A pattern
            r"(.+?)\?\s*(.+?)(?=\n\n|\n[A-Z]|$)",
        ]

        for pattern in qa_patterns:
            matches = re.finditer(pattern, content, re.DOTALL | re.IGNORECASE)
            for i, match in enumerate(matches):
                question = match.group(1).strip()
                answer = match.group(2).strip()

                # Q&A to one chunk
                qa_content = f"Q: {question}\nA: {answer}"

                # Create metadata
                metadata = ChunkMetadata(
                    doc_type="faq",
                    anchor_heading=heading,
                    summary=self._generate_summary(qa_content),
                    keywords=self._extract_keywords(qa_content),
                    links=self._extract_links(qa_content),
                )

                chunk = EnhancedChunk(
                    content=qa_content,
                    chunk_id=f"{source}_faq_{i}",
                    chunk_uid=f"{source}#faq_{i}",
                    source=source,
                    page=page,
                    metadata=metadata,
                )
                chunks.append(chunk)

        return chunks

    def _chunk_general_section(
        self,
        content: str,
        source: str,
        page: Optional[int],
        heading: Optional[str],
        doc_type: str,
    ) -> List[EnhancedChunk]:
        """General section to chunk by size"""
        chunks = []

        # Split by token (simple word count based)
        words = content.split()
        current_chunk_words = []
        chunk_index = 0

        for word in words:
            current_chunk_words.append(word)

            # Check chunk size
            if len(current_chunk_words) >= self.chunk_size:
                chunk_content = " ".join(current_chunk_words)

                # Create metadata
                metadata = ChunkMetadata(
                    doc_type=doc_type,
                    week=self._extract_week(chunk_content),
                    topic=self._extract_topic(chunk_content),
                    audience=self._extract_audience(chunk_content),
                    anchor_heading=heading,
                    summary=self._generate_summary(chunk_content),
                    keywords=self._extract_keywords(chunk_content),
                    links=self._extract_links(chunk_content),
                )

                chunk = EnhancedChunk(
                    content=chunk_content,
                    chunk_id=f"{source}_chunk_{chunk_index}",
                    chunk_uid=f"{source}#chunk_{chunk_index}",
                    source=source,
                    page=page,
                    metadata=metadata,
                )
                chunks.append(chunk)

                # Overlap processing
                overlap_words = current_chunk_words[-self.overlap_size :]
                current_chunk_words = overlap_words
                chunk_index += 1

        # Last chunk processing
        if current_chunk_words and len(current_chunk_words) >= self.min_chunk_size:
            chunk_content = " ".join(current_chunk_words)

            metadata = ChunkMetadata(
                doc_type=doc_type,
                week=self._extract_week(chunk_content),
                topic=self._extract_topic(chunk_content),
                audience=self._extract_audience(chunk_content),
                anchor_heading=heading,
                summary=self._generate_summary(chunk_content),
                keywords=self._extract_keywords(chunk_content),
                links=self._extract_links(chunk_content),
            )

            chunk = EnhancedChunk(
                content=chunk_content,
                chunk_id=f"{source}_chunk_{chunk_index}",
                chunk_uid=f"{source}#chunk_{chunk_index}",
                source=source,
                page=page,
                metadata=metadata,
            )
            chunks.append(chunk)

        return chunks

    def _extract_week(self, content: str) -> Optional[int]:
        """Extract week information"""
        patterns = [r"week\s*(\d+)", r"주차\s*(\d+)", r"(\d+)\s*주차"]  # Week patterns

        for pattern in patterns:
            match = re.search(pattern, content.lower())
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue

        return None

    def _extract_topic(self, content: str) -> Optional[str]:
        """Extract topic (simple keyword based)"""
        topics = {
            "pitch": ["pitch", "피치", "발표"],  # Pitch keywords
            "team": ["team", "팀", "매칭"],  # Team keywords
            "visa": ["visa", "비자", "opt", "cpt"],
            "training": ["training", "훈련", "트레이닝"],
            "schedule": ["schedule", "일정", "스케줄"],
        }

        content_lower = content.lower()
        for topic, keywords in topics.items():
            if any(kw in content_lower for kw in keywords):
                return topic

        return None

    def _extract_audience(self, content: str) -> str:
        """Extract audience"""
        content_lower = content.lower()

        if any(
            kw in content_lower
            for kw in ["engineer", "engineer", "development", "coding"]
        ):
            return "engineer"
        elif any(
            kw in content_lower for kw in ["pm", "product", "product", "planning"]
        ):
            return "pm"
        elif any(kw in content_lower for kw in ["designer", "design", "ui", "ux"]):
            return "designer"

        return "all"

    def _extract_links(self, content: str) -> List[str]:
        """Extract links"""
        links = []

        for pattern in self.link_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                if len(match.groups()) == 2:
                    # <title|url> format
                    links.append(f"{match.group(1)}|{match.group(2)}")
                else:
                    # URL only
                    links.append(match.group(1))

        return links

    def _generate_summary(self, content: str) -> str:
        """Generate simple summary (first sentence or core keywords)"""
        sentences = re.split(r"[.!?]+", content)
        if sentences:
            first_sentence = sentences[0].strip()
            if len(first_sentence) > 10:
                return (
                    first_sentence[:100] + "..."
                    if len(first_sentence) > 100
                    else first_sentence
                )

        return content[:100] + "..." if len(content) > 100 else content

    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords (simple frequency based)"""
        # Stop words removal
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
        }

        # Extract words and normalize
        words = re.findall(r"\b[a-zA-Z가-힣]+\b", content.lower())
        words = [w for w in words if w not in stop_words and len(w) > 2]

        # Calculate frequency
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1

        # Return top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:5]]


# Global instance
enhanced_chunker = EnhancedChunker()


def chunk_document(
    content: str, source: str, page: Optional[int] = None
) -> List[EnhancedChunk]:
    """Document chunking (convenience function)"""
    return enhanced_chunker.chunk_document(content, source, page)
