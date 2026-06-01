from pathlib import Path

import pytest

from agentpdf.core.page_ranges import parse_page_range
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.security.paths import resolve_input_path, resolve_output_path


def test_parse_comma_and_dash_range_to_zero_based_indexes() -> None:
    assert parse_page_range("1-3,7", total_pages=10) == [0, 1, 2, 6]


def test_parse_all_odd_and_even_ranges() -> None:
    assert parse_page_range("all", total_pages=5) == [0, 1, 2, 3, 4]
    assert parse_page_range("odd", total_pages=5) == [0, 2, 4]
    assert parse_page_range("even", total_pages=5) == [1, 3]


@pytest.mark.parametrize("spec", ["0", "4", "3-1", "1-", "a", ""])
def test_invalid_page_ranges_raise_stable_error(spec: str) -> None:
    with pytest.raises(AgentPDFException) as exc:
        parse_page_range(spec, total_pages=3)

    assert exc.value.code == "invalid_page_range"


def test_resolve_input_path_requires_existing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.pdf"

    with pytest.raises(AgentPDFException) as exc:
        resolve_input_path(missing)

    assert exc.value.code == "file_not_found"


def test_resolve_input_path_rejects_traversal() -> None:
    with pytest.raises(AgentPDFException) as exc:
        resolve_input_path(Path("..") / "secret.pdf")

    assert exc.value.code == "unsafe_input_rejected"


def test_resolve_output_path_creates_parent_directory(tmp_path: Path) -> None:
    output = resolve_output_path(tmp_path / "nested" / "out.pdf")

    assert output.parent.exists()
    assert output.name == "out.pdf"
