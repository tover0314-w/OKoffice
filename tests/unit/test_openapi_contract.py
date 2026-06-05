from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_static_openapi_documents_error_responses() -> None:
    openapi_text = (REPO_ROOT / "schemas" / "openapi.yaml").read_text(encoding="utf-8")

    assert "description: Tool failed or is not implemented" in openapi_text
    assert "description: Tool not found" in openapi_text
    assert "description: Job not found" in openapi_text
    assert "description: Artifact not found or missing" in openapi_text
    assert "description: Standard OKoffice error response" in openapi_text
