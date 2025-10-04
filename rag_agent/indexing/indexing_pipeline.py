from rag_agent.core.logging import logger
from rag_agent.indexing.hybrid_indexer import hybrid_index, sample_chunk_uids
from rag_agent.ingestion.chunker import chunk_text

raw_text = open("cleaned_text.txt", encoding="utf-8").read()

# B-step chunking result (e.g. previous chunk_text)
chunks = chunk_text(
    raw_text,
    max_chars=1000,
    overlap=200,
    section_path="1. Intro > 1.1 Overview",
    base_meta={"ingested_at": "2025-09-19T12:00:00Z", "checksum": "sha1:..."},
    doc_id="doc_bootcamp_journey",
    source="AI Bootcamp Journey & Learning Path.pdf",
)

# Hybrid indexing
stats = hybrid_index(
    sqlite_path="rag_kb.sqlite3",
    chunks=[c.to_dict() for c in chunks],  # Chunk → dict
    embed_model=None,  # OpenAI key exists, use None and default model
    weaviate_enabled=True,
)
logger.info(stats)  # {'sqlite_upserts':..., 'weaviate_upserts':...,
# 'sqlite_table_count':..., 'sqlite_fts_count':...}

# Random sample uid for cross-check
uids = sample_chunk_uids([c.to_dict() for c in chunks], n=5)
logger.info(f"SAMPLE UIDs: {uids}")
