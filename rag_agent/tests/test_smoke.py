import sys
from pathlib import Path

from rag_agent.core.logging import logger


def test_import_rag_modules():
    """
    Smoke test to ensure core RAG agent modules can be imported.
    """
    # Add rag_agent directory to Python path
    rag_agent_dir = Path(__file__).parent.parent
    if str(rag_agent_dir) not in sys.path:
        sys.path.insert(0, str(rag_agent_dir))

    try:
        # Test basic module imports
        import evaluation  # noqa: F401
        import generation  # noqa: F401
        import ingestion  # noqa: F401
        import retrieval  # noqa: F401

        logger.info("✅ All core RAG agent modules imported successfully")
        assert True
    except ImportError as e:
        logger.warning(f"❌ Failed to import RAG agent modules: {e}")
        assert False, f"Failed to import RAG agent modules: {e}"


def test_module_files_exist():
    """Test that required module files exist."""
    rag_agent_dir = Path(__file__).parent.parent

    required_modules = [
        "ingestion/__init__.py",
        "retrieval/__init__.py",
        "generation/__init__.py",
        "evaluation/__init__.py",
        "ingestion/pipeline.py",
        "retrieval/pipeline.py",
        "generation/generation_pipeline.py",
    ]

    for module_path in required_modules:
        full_path = rag_agent_dir / module_path
        assert full_path.exists(), f"Required module file not found: {module_path}"
        logger.info(f"✅ Found {module_path}")

    logger.info("✅ All required module files exist")
