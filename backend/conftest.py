"""
Pytest configuration for backend tests.
"""

import os
import sys
import tempfile
from pathlib import Path

# Isolate the default application engine from the developer workspace DB
# unless a live PostgreSQL URL is explicitly provided.
_existing_url = os.environ.get("DATABASE_URL", "")
if not _existing_url.startswith("postgresql"):
    _test_db = Path(tempfile.gettempdir()) / "discord_rag_bot_pytest.sqlite3"
    _test_db.unlink(missing_ok=True)
    os.environ["DATABASE_URL"] = f"sqlite:///{_test_db}"

# Never perform a live paid LLM probe during the backend test suite.
os.environ["HEALTH_LLM_PROBE_ENABLED"] = "false"

# Add backend directory to Python path for imports
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

tests_dir = backend_dir / "tests"
if str(tests_dir) not in sys.path:
    sys.path.insert(0, str(tests_dir))
