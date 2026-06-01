from __future__ import annotations

import argparse
import json
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
    parser = argparse.ArgumentParser(description="Check whether okpdf local development is ready.")
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
        "agentpdf_import": check_agentpdf_import(),
        "node": check_command("node", "--version"),
        "npm": check_command("npm", "--version"),
        "node_workspace": check_node_workspace(),
    }
    status = "ok" if all(item["ok"] for item in checks.values()) else "needs_attention"
    return {
        "status": status,
        "checks": checks,
        "next_steps": next_steps(checks),
    }


def check_python() -> dict[str, Any]:
    version = ".".join(str(part) for part in sys.version_info[:3])
    return {
        "ok": sys.version_info >= (3, 11),
        "version": version,
        "message": "Python 3.11+ is available." if sys.version_info >= (3, 11) else "Install Python 3.11+.",
    }


def check_agentpdf_import() -> dict[str, Any]:
    try:
        import agentpdf

        return {
            "ok": True,
            "version": agentpdf.__version__,
            "message": "agentpdf imports from the local workspace.",
        }
    except Exception as exc:  # pragma: no cover - defensive report path
        return {
            "ok": False,
            "message": f"Could not import agentpdf: {exc}",
        }


def check_command(command: str, version_arg: str) -> dict[str, Any]:
    executable = shutil.which(command)
    if executable is None:
        return {
            "ok": False,
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
        "path": executable,
        "version": output,
        "message": f"{command} is available.",
    }


def check_node_workspace() -> dict[str, Any]:
    package_json = ROOT / "packages" / "agentpdf-node" / "package.json"
    return {
        "ok": package_json.exists(),
        "message": "TypeScript package workspace is present."
        if package_json.exists()
        else "packages/agentpdf-node is missing.",
    }


def next_steps(checks: dict[str, dict[str, Any]]) -> list[str]:
    steps: list[str] = []
    if not checks["python"]["ok"]:
        steps.append("Install Python 3.11 or newer.")
    if not checks["agentpdf_import"]["ok"]:
        steps.append("Run: python scripts/setup_dev.py --python-only")
    if not checks["node"]["ok"] or not checks["npm"]["ok"]:
        steps.append("Install Node.js 20 or newer to use the TypeScript SDK.")
    if not steps:
        steps.append("Run: python scripts/smoke.py")
    return steps


def print_text_report(report: dict[str, Any]) -> None:
    print(f"okpdf doctor: {report['status']}")
    for name, check in report["checks"].items():
        marker = "ok" if check["ok"] else "needs attention"
        version = f" ({check['version']})" if check.get("version") else ""
        print(f"- {name}: {marker}{version}")
        print(f"  {check['message']}")
    print("Next:")
    for step in report["next_steps"]:
        print(f"- {step}")


if __name__ == "__main__":
    raise SystemExit(main())
