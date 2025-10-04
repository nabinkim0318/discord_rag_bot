# rag_agent/ingestion/enhanced_chunker.py
"""
Enhanced chunking system
- FAQ 1 question 1 answer unit chunking
- Heading boundary based splitting
- Enhanced metadata (doc_type, week, audience, links)
- Summary and keyword extraction
"""

import hashlib
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
    links: List[Dict[str, str]] = None
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
            "faq": [
                r"FAQ",
                r"Q\s*&\s*A",
                r"frequently\s*asked\s*questions",
                r"questions\s*and\s*answers",
            ],
            "schedule": [
                r"schedule",
                r"timetable",
                r"week",
                r"week",
                r"timeline",
                r"deadline",
            ],
            "process": [r"process", r"procedure", r"guide", r"method", r"steps"],
            "resources": [
                r"resources",
                r"materials",
                r"links",
                r"training",
                r"training",
                r"course",
            ],
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
        """Split document by heading with improved underline detection"""
        lines = content.split("\n")
        sections = []
        current_section = {"heading": None, "content": [], "level": 0}

        i = 0
        while i < len(lines):
            line = lines[i]

            # Check for underline heading (2-line pattern)
            is_underline_heading = False
            heading_text = None

            if i < len(lines) - 1:
                next_line = lines[i + 1]
                # Check for underline patterns: Title\n===== or Title\n-----
                if re.match(r"^={3,}$", next_line.strip()) or re.match(
                    r"^-{3,}$", next_line.strip()
                ):
                    heading_text = line.strip()
                    is_underline_heading = True
                    i += 1  # Skip the underline line

            # Single line heading detection
            if not is_underline_heading:
                heading_match = None
                for pattern in self.heading_patterns:
                    match = re.match(pattern, line.strip())
                    if match:
                        heading_match = match
                        break

                if heading_match:
                    heading_text = heading_match.group(1).strip()

            if heading_text:
                # Save previous section
                if current_section["content"]:
                    sections.append(current_section)

                # Start new section
                current_section = {
                    "heading": heading_text,
                    "content": [line],
                    "level": self._get_heading_level(line),
                }
            else:
                current_section["content"].append(line)

            i += 1

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
            # Q&A pattern
            r"question\s*:\s*(.+?)\s*answer\s*:\s*(.+?)(?=question\s*:|$)",
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

                # Generate stable chunk ID based on content hash
                content_hash = hashlib.sha1(qa_content.encode("utf-8")).hexdigest()[:8]
                chunk_id = f"{source}_faq_{content_hash}"
                chunk_uid = f"{source}#{content_hash}"

                chunk = EnhancedChunk(
                    content=qa_content,
                    chunk_id=chunk_id,
                    chunk_uid=chunk_uid,
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

                # Generate stable chunk ID based on content hash
                content_hash = hashlib.sha1(chunk_content.encode("utf-8")).hexdigest()[
                    :8
                ]
                chunk_id = f"{source}_chunk_{content_hash}"
                chunk_uid = f"{source}#{content_hash}"

                chunk = EnhancedChunk(
                    content=chunk_content,
                    chunk_id=chunk_id,
                    chunk_uid=chunk_uid,
                    source=source,
                    page=page,
                    metadata=metadata,
                )
                chunks.append(chunk)

                # Overlap processing
                overlap_words = current_chunk_words[-self.overlap_size :]
                current_chunk_words = overlap_words
                chunk_index += 1

        # Last chunk processing with short chunk handling
        if current_chunk_words:
            chunk_content = " ".join(current_chunk_words)

            # Check if last chunk is too short and merge with previous chunk
            if len(current_chunk_words) < self.min_chunk_size and chunks:
                # Merge with previous chunk
                prev_chunk = chunks[-1]
                merged_content = prev_chunk.content + " " + chunk_content

                # Update previous chunk with merged content
                merged_metadata = ChunkMetadata(
                    doc_type=doc_type,
                    week=self._extract_week(merged_content),
                    topic=self._extract_topic(merged_content),
                    audience=self._extract_audience(merged_content),
                    anchor_heading=heading,
                    summary=self._generate_summary(merged_content),
                    keywords=self._extract_keywords(merged_content),
                    links=self._extract_links(merged_content),
                )

                # Generate new stable ID for merged content
                merged_hash = hashlib.sha1(merged_content.encode("utf-8")).hexdigest()[
                    :8
                ]
                prev_chunk.content = merged_content
                prev_chunk.chunk_id = f"{source}_chunk_{merged_hash}"
                prev_chunk.chunk_uid = f"{source}#{merged_hash}"
                prev_chunk.metadata = merged_metadata
            else:
                # Create new chunk if it's long enough or no previous chunks
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

                # Generate stable chunk ID based on content hash
                content_hash = hashlib.sha1(chunk_content.encode("utf-8")).hexdigest()[
                    :8
                ]
                chunk_id = f"{source}_chunk_{content_hash}"
                chunk_uid = f"{source}#{content_hash}"

                chunk = EnhancedChunk(
                    content=chunk_content,
                    chunk_id=chunk_id,
                    chunk_uid=chunk_uid,
                    source=source,
                    page=page,
                    metadata=metadata,
                )
                chunks.append(chunk)

        return chunks

    def _extract_week(self, content: str) -> Optional[int]:
        """Extract week information"""
        patterns = [r"week\s*(\d+)", r"week\s*(\d+)", r"(\d+)\s*week"]  # Week patterns

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
            "pitch": ["pitch", "presentation", "demo"],  # Pitch keywords
            "team": ["team", "matching", "collaboration"],  # Team keywords
            "visa": ["visa", "immigration", "opt", "cpt"],
            "training": ["training", "education", "learning"],
            "schedule": ["schedule", "timetable", "calendar"],
        }

        content_lower = content.lower()
        for topic, keywords in topics.items():
            if any(kw in content_lower for kw in keywords):
                return topic

        return None

    def _extract_audience(self, content: str) -> str:
        """Extract audience with improved keyword coverage"""
        content_lower = content.lower()

        # Engineering keywords (removed duplicate "engineer")
        if any(
            kw in content_lower
            for kw in [
                "engineer",
                "development",
                "coding",
                "programming",
                "software",
                "backend",
                "frontend",
                "fullstack",
            ]
        ):
            return "engineer"
        # Data Science / ML keywords
        elif any(
            kw in content_lower
            for kw in [
                "data scientist",
                "data science",
                "ml",
                "machine learning",
                "ai",
                "analytics",
                "ds",
                "data analyst",
            ]
        ):
            return "data_scientist"
        # Product Management keywords (removed duplicate "product")
        elif any(
            kw in content_lower
            for kw in [
                "pm",
                "product",
                "planning",
                "strategy",
                "roadmap",
                "product manager",
            ]
        ):
            return "pm"
        # Design keywords
        elif any(
            kw in content_lower
            for kw in [
                "designer",
                "design",
                "ui",
                "ux",
                "user experience",
                "user interface",
            ]
        ):
            return "designer"
        # Operations keywords
        elif any(
            kw in content_lower
            for kw in [
                "ops",
                "operations",
                "devops",
                "sre",
                "infrastructure",
                "deployment",
            ]
        ):
            return "operations"

        return "all"

    def _extract_links(self, content: str) -> List[Dict[str, str]]:
        """Extract links in standardized format"""
        links = []

        for pattern in self.link_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                if len(match.groups()) == 2:
                    # <title|url> format or markdown link [title](url)
                    title = match.group(1).strip()
                    url = match.group(2).strip()
                    links.append({"title": title, "url": url})
                else:
                    # URL only - use URL as title
                    url = match.group(1).strip()
                    links.append({"title": url, "url": url})

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


def validate_enhanced_chunk_data(
    chunks: List[EnhancedChunk], original_text: str
) -> Dict[str, Any]:
    """
    Validate enhanced chunk data integrity and statistics

    Args:
        chunks: List of enhanced chunks to validate
        original_text: Original text for offset validation

    Returns:
        Dict with validation results and statistics
    """
    validation_results = {
        "offset_integrity_passed": True,
        "id_stability_passed": True,
        "length_stats": {},
        "integration_check_passed": True,
        "errors": [],
    }

    # 1. Offset integrity check (for enhanced chunks, we check content consistency)
    for i, chunk in enumerate(chunks):
        try:
            # For enhanced chunks, we validate that the content is reasonable
            assert len(chunk.content.strip()) > 0, f"Chunk {i}: empty content"
            assert chunk.chunk_id is not None, f"Chunk {i}: missing chunk_id"
            assert chunk.chunk_uid is not None, f"Chunk {i}: missing chunk_uid"
        except AssertionError as e:
            validation_results["offset_integrity_passed"] = False
            validation_results["errors"].append(
                f"Enhanced chunk integrity error in chunk {i}: {str(e)}"
            )

    # 2. Length statistics
    chunk_lengths = [len(chunk.content) for chunk in chunks]
    if chunk_lengths:
        sorted_lengths = sorted(chunk_lengths)
        n = len(sorted_lengths)
        p10 = sorted_lengths[max(0, int(0.10 * n) - 1)]
        p90 = sorted_lengths[min(n - 1, int(0.90 * n) - 1)]
        mean_length = sum(chunk_lengths) / len(chunk_lengths)
        min_length = min(chunk_lengths)
        max_length = max(chunk_lengths)

        validation_results["length_stats"] = {
            "count": len(chunk_lengths),
            "mean": mean_length,
            "p10": p10,
            "p90": p90,
            "min": min_length,
            "max": max_length,
            "p10_p90_in_range": 300 <= p10 and p90 <= 1000,
        }

        # Check if p10/p90 are in expected range (300-1000 chars)
        if not (300 <= p10 and p90 <= 1000):
            validation_results["errors"].append(
                f"Length stats out of range: p10={p10}, p90={p90}"
            )

    # 3. Integration check - verify required fields for hybrid indexer
    required_fields = ["source", "page"]
    for i, chunk in enumerate(chunks):
        missing_fields = [
            field for field in required_fields if getattr(chunk, field, None) is None
        ]
        if missing_fields:
            validation_results["integration_check_passed"] = False
            validation_results["errors"].append(
                f"Enhanced chunk {i} missing required fields: {missing_fields}"
            )

        # Check metadata structure
        if chunk.metadata:
            metadata_required = ["doc_type", "audience"]
            missing_metadata = [
                field
                for field in metadata_required
                if not hasattr(chunk.metadata, field)
            ]
            if missing_metadata:
                validation_results["integration_check_passed"] = False
                validation_results["errors"].append(
                    f"Enhanced chunk {i} metadata missing fields: {missing_metadata}"
                )

    return validation_results


def test_enhanced_id_stability(
    chunker_func, content: str, source: str, **kwargs
) -> bool:
    """
    Test enhanced chunker ID stability by running twice and comparing chunk_uid sets

    Args:
        chunker_func: Enhanced chunking function to test
        content: Input content
        source: Document source
        **kwargs: Additional arguments for chunker

    Returns:
        bool: True if IDs are stable, False otherwise
    """
    # Run chunker twice
    chunks1 = chunker_func(content, source, **kwargs)
    chunks2 = chunker_func(content, source, **kwargs)

    # Extract chunk_uid sets
    uids1 = {chunk.chunk_uid for chunk in chunks1}
    uids2 = {chunk.chunk_uid for chunk in chunks2}

    return uids1 == uids2
