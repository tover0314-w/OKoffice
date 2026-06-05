from pathlib import Path

from okoffice.schemas.errors import KNOWN_ERROR_CODES


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_known_error_codes_match_yaml_catalog() -> None:
    yaml_path = REPO_ROOT / "schemas" / "error-codes.yaml"
    yaml_codes = set()
    in_error_codes = False
    for line in yaml_path.read_text(encoding="utf-8").splitlines():
        if line.strip() == "error_codes:":
            in_error_codes = True
            continue
        if in_error_codes and line.startswith("  ") and ":" in line:
            yaml_codes.add(line.strip().split(":", 1)[0])

    assert KNOWN_ERROR_CODES == yaml_codes
