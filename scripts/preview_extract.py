# scripts/preview_extract.py
from rag_agent.ingestion.loader import load_many_pdfs


def preview(records, n=3, preview_chars=500):
    print(f"\nTotal pages extracted: {len(records)}")
    for i, r in enumerate(records[:n], 1):
        m = r.meta
        print("=" * 80)
        print(f"[{i}] {m.source}  |  title={m.title}  |  page={m.page}")
        print(f"section={m.section_title}  |  checksum={m.checksum[:10]}...")
        print("-" * 80)
        print(r.text[:preview_chars].strip())
        print()


if __name__ == "__main__":
    pdfs = [
        "rag_agent/data/raw_docs/AI Bootcamp Journey & Learning Path.docx (1).pdf",
        "rag_agent/data/raw_docs/Intern FAQ - AI Bootcamp (2).pdf",
        "rag_agent/data/raw_docs/Training For AI Engineer Interns (2).pdf",
    ]
    records = load_many_pdfs(pdfs)
    preview(records, n=5)
