from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_okpdf_console_script_alias_is_declared() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert data["project"]["scripts"]["agentpdf"] == "okoffice.cli.main:app"
    assert data["project"]["scripts"]["okpdf"] == "okoffice.cli.main:app"


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
    assert payload["checks"]["okoffice_import"]["ok"] is True
    assert payload["checks"]["node"]["ok"] is True
    for check_name in [
        "pypdf",
        "pypdfium2",
        "reportlab",
        "fastapi",
        "mcp",
        "typer",
        "cli_help",
        "rest_app",
        "mcp_server",
    ]:
        assert payload["checks"][check_name]["ok"] is True
        assert payload["checks"][check_name]["required"] is True
    assert payload["checks"]["tesseract"]["required"] is False
    assert payload["checks"]["tesseract"]["category"] == "optional_runtime"
    assert payload["checks"]["cjk_fonts"]["required"] is False
    assert "optional_next_steps" in payload


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


def test_docker_self_hosted_entrypoint_is_declared() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")

    assert "FROM python:3.12-slim" in dockerfile
    assert "python -m pip install -e ." in dockerfile
    assert "USER okoffice" in dockerfile
    assert 'ENTRYPOINT ["okoffice"]' in dockerfile
    assert 'CMD ["serve", "--api", "--host", "0.0.0.0", "--port", "7331", "--safe-root", "/workspace"]' in dockerfile
    assert "EXPOSE 7331" in dockerfile

    assert "7331:7331" in compose
    assert ".:/workspace" in compose
    assert "serve --api" in compose
    assert "0.0.0.0" in compose
    assert "/healthz" in compose

    for ignored_path in [".git", "node_modules", ".okoffice-out", ".pytest-tmp", "packages/*/dist"]:
        assert ignored_path in dockerignore
