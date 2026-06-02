from pathlib import Path

from pypdf import PdfReader


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_github_label_config_covers_maintainer_triage_labels() -> None:
    labels_path = REPO_ROOT / ".github" / "labels.yml"

    labels_text = labels_path.read_text(encoding="utf-8")

    for label in [
        "area:cli",
        "area:mcp",
        "area:api",
        "area:pdf-core",
        "area:validation",
        "area:docs",
        "area:security",
        "status:planned",
        "status:beta",
        "good first issue",
        "help wanted",
    ]:
        assert f"name: {label}" in labels_text


def test_visual_placeholders_are_documented() -> None:
    placeholder_path = REPO_ROOT / "docs" / "assets" / "screenshots" / "README.md"

    placeholder_text = placeholder_path.read_text(encoding="utf-8")

    assert "CLI smoke output" in placeholder_text
    assert "MCP tool discovery" in placeholder_text
    assert "REST API docs" in placeholder_text
    assert ".gif" in placeholder_text


def test_example_generated_pdf_is_committed_and_readable() -> None:
    pdf_path = REPO_ROOT / "examples" / "generated" / "hello.pdf"

    reader = PdfReader(pdf_path)

    assert len(reader.pages) == 1
