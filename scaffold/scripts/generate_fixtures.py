"""Generate small, license-safe fixture PDFs for tests.

Codex should implement this once PDF dependencies are selected.
"""
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures"

if __name__ == "__main__":
    FIXTURES.mkdir(parents=True, exist_ok=True)
    print(f"TODO: generate fixture PDFs in {FIXTURES}")
