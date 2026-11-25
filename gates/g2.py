"""G2: round-trip tests for each key/syllabus input mode (paste, .txt, .pdf), keyless => key_source='ai', redaction."""
import sys
from common import pytest_gate

sys.exit(0 if pytest_gate("G2", "tests/test_g2_setup.py") else 1)
