from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_okpdf_console_script_alias_is_declared() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert data["project"]["scripts"]["agentpdf"] == "agentpdf.cli.main:app"
    assert data["project"]["scripts"]["okpdf"] == "agentpdf.cli.main:app"


def test_doctor_reports_ready_json() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/doctor.py", "--json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["checks"]["python"]["ok"] is True
    assert payload["checks"]["agentpdf_import"]["ok"] is True
    assert payload["checks"]["node"]["ok"] is True


def test_smoke_script_creates_local_pdf_artifact(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "scripts/smoke.py", "--out-dir", str(tmp_path), "--json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["artifacts"]["created_pdf"].endswith("hello.pdf")
    assert (tmp_path / "hello.pdf").exists()
