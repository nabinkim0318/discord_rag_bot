# scripts/preview_extract.py
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rag_agent.core.logging import logger  # noqa: E402
from rag_agent.ingestion.loader import load_many_pdfs  # noqa: E402


def preview(records, n=3, preview_chars=500):
    logger.info(f"\nTotal pages extracted: {len(records)}")
    for i, r in enumerate(records[:n], 1):
        m = r.meta
        logger.info("=" * 80)
        logger.info(f"[{i}] {m.source}  |  title={m.title}  |  page={m.page}")
        logger.info(f"section={m.section_title}  |  checksum={m.checksum[:10]}...")
        logger.info("-" * 80)
        logger.info(r.text[:preview_chars].strip())
        logger.info()


if __name__ == "__main__":
    pdfs = [
        "data/raw_docs/AI Bootcamp Journey & Learning Path.docx.pdf",
        "data/raw_docs/Intern FAQ - AI Bootcamp.pdf",
        "data/raw_docs/Training For AI Engineer Interns.pdf",
    ]
    records = load_many_pdfs(pdfs)
    preview(records, n=5)
