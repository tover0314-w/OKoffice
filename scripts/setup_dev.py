from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Install OKoffice for local development.")
    parser.add_argument("--python-only", action="store_true", help="Only install Python dependencies.")
    parser.add_argument("--skip-node", action="store_true", help="Skip npm install and Node build.")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without running them.")
    args = parser.parse_args()

    commands = [
        [sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
    ]
    if not args.python_only and not args.skip_node:
        commands.extend(
            [
                ["npm", "install"],
                ["npm", "run", "build:node"],
            ]
        )

    for command in commands:
        print("$ " + " ".join(command))
        if not args.dry_run:
            subprocess.run(command, cwd=ROOT, check=True)

    print("\nReady. Try:")
    print("  python scripts/doctor.py")
    print("  python scripts/smoke.py")
    print("  okoffice tools list")
    print("  okoffice agent setup claude-code --output .mcp.json --json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
