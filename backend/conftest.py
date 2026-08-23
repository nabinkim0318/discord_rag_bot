"""
Pytest configuration for backend tests.
"""

import sys
from pathlib import Path

# Add backend directory to Python path for imports
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

tests_dir = backend_dir / "tests"
if str(tests_dir) not in sys.path:
    sys.path.insert(0, str(tests_dir))
