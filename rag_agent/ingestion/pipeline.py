"""
Ingestion Pipeline for RAG Agent

This module provides the main ingestion pipeline that orchestrates
document loading, processing, chunking, and storage.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .chunker import chunk_documents
from .enhanced_chunker import enhanced_chunk_documents
from .loader import load_documents
from .normalize import normalize_text
from .schema import Chunk, Document

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Main ingestion pipeline for processing documents."""

    def __init__(self, use_enhanced_chunker: bool = True):
        """
        Initialize the ingestion pipeline.

        Args:
            use_enhanced_chunker: Whether to use enhanced chunker (default: True)
        """
        self.use_enhanced_chunker = use_enhanced_chunker

    def process_documents(
        self, input_path: str, output_path: Optional[str] = None, **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Process documents through the full ingestion pipeline.

        Args:
            input_path: Path to input documents
            output_path: Path to save processed chunks (optional)
            **kwargs: Additional parameters for processing

        Returns:
            List of processed chunks with metadata
        """
        try:
            # 1. Load documents
            logger.info(f"Loading documents from {input_path}")
            documents = load_documents(input_path)
            logger.info(f"Loaded {len(documents)} documents")

            # 2. Normalize text
            logger.info("Normalizing document text")
            normalized_docs = []
            for doc in documents:
                normalized_text = normalize_text(doc.content)
                normalized_doc = Document(
                    content=normalized_text, metadata=doc.metadata, source=doc.source
                )
                normalized_docs.append(normalized_doc)

            # 3. Chunk documents
            logger.info("Chunking documents")
            if self.use_enhanced_chunker:
                chunks = enhanced_chunk_documents(normalized_docs, **kwargs)
            else:
                chunks = chunk_documents(normalized_docs, **kwargs)

            logger.info(f"Generated {len(chunks)} chunks")

            # 4. Save chunks if output path provided
            if output_path:
                self._save_chunks(chunks, output_path)

            return chunks

        except Exception as e:
            logger.error(f"Error in ingestion pipeline: {e}")
            raise

    def _save_chunks(self, chunks: List[Chunk], output_path: str) -> None:
        """
        Save chunks to output path.

        Args:
            chunks: List of chunks to save
            output_path: Path to save chunks
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Convert chunks to serializable format
        chunk_data = []
        for chunk in chunks:
            chunk_data.append(
                {
                    "content": chunk.content,
                    "metadata": chunk.metadata,
                    "chunk_id": getattr(chunk, "chunk_id", None),
                    "source": getattr(chunk, "source", None),
                }
            )

        # Save as JSON (simple implementation)
        import json

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(chunk_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(chunks)} chunks to {output_path}")


def run_ingestion_pipeline(
    input_path: str,
    output_path: Optional[str] = None,
    use_enhanced_chunker: bool = True,
    **kwargs,
) -> List[Dict[str, Any]]:
    """
    Run the complete ingestion pipeline.

    Args:
        input_path: Path to input documents
        output_path: Path to save processed chunks (optional)
        use_enhanced_chunker: Whether to use enhanced chunker
        **kwargs: Additional parameters for processing

    Returns:
        List of processed chunks with metadata
    """
    pipeline = IngestionPipeline(use_enhanced_chunker=use_enhanced_chunker)
    return pipeline.process_documents(input_path, output_path, **kwargs)


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <input_path> [output_path]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        chunks = run_ingestion_pipeline(input_path, output_path)
        print(f"Successfully processed {len(chunks)} chunks")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
