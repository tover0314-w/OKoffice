from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

def main() -> int:
    parser = argparse.ArgumentParser(description="Run a tiny okoffice local smoke test.")
    parser.add_argument("--out-dir", type=Path, default=Path(".okoffice-out/smoke"))
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    report = run_smoke(args.out_dir)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_text_report(report)
    return 0 if report["status"] == "ok" else 1


def run_smoke(out_dir: Path) -> dict[str, Any]:
    from okoffice.tools.runner import run_create_text, run_extract_text, run_inspect

    out_dir.mkdir(parents=True, exist_ok=True)
    created_pdf = out_dir / "hello.pdf"

    created = run_create_text("Hello from okoffice smoke test.", created_pdf)
    inspected = run_inspect(created_pdf)
    extracted = run_extract_text(created_pdf)

    checks = {
        "create_text_pdf": created.status == "succeeded",
        "inspect_created_pdf": inspected.status == "succeeded",
        "extract_text": extracted.status == "succeeded"
        and "Hello from okoffice smoke test." in str(extracted.usage.get("text", "")),
    }

    return {
        "status": "ok" if all(checks.values()) else "failed",
        "checks": checks,
        "artifacts": {
            "created_pdf": str(created_pdf.resolve()),
        },
        "tool_results": {
            "create": created.model_dump(mode="json"),
            "inspect": inspected.model_dump(mode="json"),
            "extract_text": extracted.model_dump(mode="json"),
        },
    }


def print_text_report(report: dict[str, Any]) -> None:
    print(f"okoffice smoke: {report['status']}")
    for name, ok in report["checks"].items():
        print(f"- {name}: {'ok' if ok else 'failed'}")
    print(f"Created: {report['artifacts']['created_pdf']}")


if __name__ == "__main__":
    raise SystemExit(main())
