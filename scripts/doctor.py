from __future__ import annotations

import argparse
import importlib
import importlib.metadata as package_metadata
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether okoffice local development is ready.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    report = build_report()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_text_report(report)
    return 0 if report["status"] == "ok" else 1


def build_report() -> dict[str, Any]:
    checks = {
        "python": check_python(),
        "okoffice_import": check_okoffice_import(),
        "pypdf": check_import("pypdf"),
        "pypdfium2": check_import("pypdfium2"),
        "reportlab": check_import("reportlab"),
        "fastapi": check_import("fastapi"),
        "mcp": check_import("mcp"),
        "typer": check_import("typer"),
        "node": check_command("node", "--version"),
        "npm": check_command("npm", "--version"),
        "node_workspace": check_node_workspace(),
        "cli_help": check_cli_help(),
        "rest_app": check_rest_app(),
        "mcp_server": check_mcp_server(),
        "tesseract": check_tesseract(),
        "cjk_fonts": check_cjk_fonts(),
    }
    required_checks = [item for item in checks.values() if item.get("required", True)]
    status = "ok" if all(item["ok"] for item in required_checks) else "needs_attention"
    return {
        "status": status,
        "checks": checks,
        "next_steps": next_steps(checks),
        "optional_next_steps": optional_next_steps(checks),
    }


def check_python() -> dict[str, Any]:
    version = ".".join(str(part) for part in sys.version_info[:3])
    return {
        "ok": sys.version_info >= (3, 11),
        "required": True,
        "category": "required_runtime",
        "version": version,
        "message": "Python 3.11+ is available." if sys.version_info >= (3, 11) else "Install Python 3.11+.",
    }


def check_okoffice_import() -> dict[str, Any]:
    try:
        import okoffice

        return {
            "ok": True,
            "required": True,
            "category": "required_runtime",
            "version": okoffice.__version__,
            "message": "okoffice imports from the local workspace.",
        }
    except Exception as exc:  # pragma: no cover - defensive report path
        return {
            "ok": False,
            "required": True,
            "category": "required_runtime",
            "message": f"Could not import okoffice: {exc}",
        }


def check_import(module_name: str, distribution_name: str | None = None) -> dict[str, Any]:
    try:
        importlib.import_module(module_name)
        version = _package_version(distribution_name or module_name)
        return {
            "ok": True,
            "required": True,
            "category": "required_runtime",
            "version": version,
            "message": f"{module_name} imports successfully.",
        }
    except Exception as exc:
        return {
            "ok": False,
            "required": True,
            "category": "required_runtime",
            "message": f"Could not import {module_name}: {exc}",
        }


def check_command(
    command: str,
    version_arg: str,
    *,
    required: bool = True,
    category: str = "required_runtime",
) -> dict[str, Any]:
    executable = shutil.which(command)
    if executable is None:
        return {
            "ok": False,
            "required": required,
            "category": category,
            "message": f"{command} was not found on PATH.",
        }
    result = subprocess.run(
        [executable, version_arg],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    output = (result.stdout or result.stderr).strip()
    return {
        "ok": result.returncode == 0,
        "required": required,
        "category": category,
        "path": executable,
        "version": output,
        "message": f"{command} is available.",
    }


def check_node_workspace() -> dict[str, Any]:
    package_json = ROOT / "packages" / "okoffice-node" / "package.json"
    return {
        "ok": package_json.exists(),
        "required": True,
        "category": "required_runtime",
        "message": "TypeScript package workspace is present."
        if package_json.exists()
        else "packages/okoffice-node is missing.",
    }


def check_cli_help() -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    compatibility_result = subprocess.run(
        [sys.executable, "-m", "okoffice.cli", "--help"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    public_result = subprocess.run(
        [sys.executable, "-m", "okoffice.cli_okoffice", "--help"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    compatibility_output = (compatibility_result.stdout or compatibility_result.stderr).strip()
    public_output = (public_result.stdout or public_result.stderr).strip()
    compatibility_ok = (
        compatibility_result.returncode == 0
        and "OKoffice agent-native Office infra CLI" in compatibility_output
    )
    public_ok = public_result.returncode == 0 and "OKoffice agent-native Office infra CLI" in public_output
    return {
        "ok": compatibility_ok and public_ok,
        "required": True,
        "category": "required_runtime",
        "message": "okoffice compatibility CLI and okoffice public CLI help both work."
        if compatibility_ok and public_ok
        else "Run python -m okoffice.cli --help and python -m okoffice.cli_okoffice --help to inspect CLI setup.",
    }


def check_rest_app() -> dict[str, Any]:
    try:
        from okoffice.api.app import create_app

        app = create_app()
        routes = sorted(getattr(route, "path", "") for route in app.routes)
        return {
            "ok": "/healthz" in routes and "/v1/tools" in routes,
            "required": True,
            "category": "required_runtime",
            "route_count": len(routes),
            "message": "REST app imports and exposes local health/tool routes.",
        }
    except Exception as exc:
        return {
            "ok": False,
            "required": True,
            "category": "required_runtime",
            "message": f"REST app import failed: {exc}",
        }


def check_mcp_server() -> dict[str, Any]:
    try:
        from okoffice.mcp.server import create_mcp_server

        create_mcp_server()
        return {
            "ok": True,
            "required": True,
            "category": "required_runtime",
            "message": "MCP server imports and registers local tools.",
        }
    except Exception as exc:
        return {
            "ok": False,
            "required": True,
            "category": "required_runtime",
            "message": f"MCP server import failed: {exc}",
        }


def check_tesseract() -> dict[str, Any]:
    check = check_command(
        "tesseract",
        "--version",
        required=False,
        category="optional_runtime",
    )
    if check["ok"]:
        check["message"] = "Tesseract OCR is available for pdf.ocr_scan.* tools."
    else:
        check["message"] = "Tesseract OCR is optional and was not found on PATH."
    return check


def check_cjk_fonts() -> dict[str, Any]:
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont

        from okoffice.core.pdf import CJK_CID_FONT, CJK_FONT_CANDIDATES, CJK_FONT_PATH_ENV

        configured = [
            Path(raw_path.strip())
            for raw_path in os.environ.get(CJK_FONT_PATH_ENV, "").split(os.pathsep)
            if raw_path.strip()
        ]
        candidates = configured + list(CJK_FONT_CANDIDATES)
        found = [str(candidate) for candidate in candidates if candidate.exists()]
        cid_fallback = False
        if not found:
            try:
                pdfmetrics.registerFont(UnicodeCIDFont(CJK_CID_FONT))
                cid_fallback = True
            except Exception:
                cid_fallback = False
        ok = bool(found) or cid_fallback
        return {
            "ok": ok,
            "required": False,
            "category": "optional_runtime",
            "found": found,
            "cid_fallback": cid_fallback,
            "message": "A CJK-capable font is available."
            if ok
            else "No CJK-capable font candidate was found.",
        }
    except Exception as exc:
        return {
            "ok": False,
            "required": False,
            "category": "optional_runtime",
            "message": f"CJK font check failed: {exc}",
        }


def next_steps(checks: dict[str, dict[str, Any]]) -> list[str]:
    steps: list[str] = []
    if not checks["python"]["ok"]:
        steps.append("Install Python 3.11 or newer.")
    if not checks["okoffice_import"]["ok"]:
        steps.append("Run: python scripts/setup_dev.py --python-only")
    for name in ["pypdf", "pypdfium2", "reportlab", "fastapi", "mcp", "typer"]:
        if not checks[name]["ok"]:
            steps.append(f"Install missing Python dependency: {name}")
    if not checks["node"]["ok"] or not checks["npm"]["ok"]:
        steps.append("Install Node.js 20 or newer to use the TypeScript SDK.")
    if not checks["cli_help"]["ok"]:
        steps.append("Run: python -m okoffice.cli --help and python -m okoffice.cli_okoffice --help")
    if not checks["rest_app"]["ok"] or not checks["mcp_server"]["ok"]:
        steps.append("Check local package imports and rerun: pytest tests/integration/test_api.py -q")
    if not steps:
        steps.append("Run: python scripts/smoke.py")
    return steps


def optional_next_steps(checks: dict[str, dict[str, Any]]) -> list[str]:
    steps: list[str] = []
    if not checks["tesseract"]["ok"]:
        steps.append("Install Tesseract OCR and language packs, then rerun: python scripts/doctor.py")
    if not checks["cjk_fonts"]["ok"]:
        steps.append("Install a CJK-capable font or set AGENTPDF_CJK_FONT_PATH.")
    return steps


def print_text_report(report: dict[str, Any]) -> None:
    print(f"okoffice doctor: {report['status']}")
    for name, check in report["checks"].items():
        if check["ok"]:
            marker = "ok"
        elif check.get("required", True):
            marker = "needs attention"
        else:
            marker = "optional missing"
        version = f" ({check['version']})" if check.get("version") else ""
        print(f"- {name}: {marker}{version}")
        print(f"  {check['message']}")
    print("Next:")
    for step in report["next_steps"]:
        print(f"- {step}")
    if report.get("optional_next_steps"):
        print("Optional:")
        for step in report["optional_next_steps"]:
            print(f"- {step}")


def _package_version(distribution_name: str) -> str | None:
    try:
        return package_metadata.version(distribution_name)
    except package_metadata.PackageNotFoundError:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
