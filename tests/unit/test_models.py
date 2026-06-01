from pathlib import Path

from agentpdf.schemas.models import (
    AgentPDFError,
    Artifact,
    FileRef,
    ToolManifest,
    ToolResult,
    ToolSpec,
    ValidationCheck,
    ValidationReport,
)


def test_tool_result_serializes_uniform_contract() -> None:
    artifact = Artifact(
        artifact_id="art_123",
        path=Path("out.pdf"),
        mime_type="application/pdf",
        size_bytes=12,
        sha256="abc",
        source_tool="pdf.organize.merge",
        page_count=1,
    )
    validation = ValidationReport(
        status="passed",
        checks=[ValidationCheck(name="page_count", status="passed", details={"pages": 1})],
    )

    result = ToolResult(
        job_id="job_123",
        status="succeeded",
        tool="pdf.organize.merge",
        artifacts=[artifact],
        validation=validation,
        warnings=[],
        usage={"inputs": 2},
        next_recommended_tools=["pdf.inspect.document"],
    )

    payload = result.model_dump(mode="json")

    assert payload["job_id"] == "job_123"
    assert payload["status"] == "succeeded"
    assert payload["artifacts"][0]["path"] == "out.pdf"
    assert payload["validation"]["status"] == "passed"
    assert result.model_dump_json()


def test_failed_tool_result_contains_stable_error() -> None:
    result = ToolResult(
        job_id="job_failed",
        status="failed",
        tool="pdf.inspect.document",
        error=AgentPDFError(code="file_not_found", message="Input file not found."),
    )

    payload = result.model_dump(mode="json")

    assert payload["error"]["code"] == "file_not_found"
    assert payload["artifacts"] == []
    assert payload["warnings"] == []


def test_tool_manifest_serializes_tool_specs() -> None:
    manifest = ToolManifest(
        tools=[
            ToolSpec(
                name="pdf.inspect.document",
                status="stable",
                description="Inspect a PDF document.",
                category="inspect",
                interfaces=["cli", "mcp", "rest"],
                implemented=True,
            )
        ]
    )

    payload = manifest.model_dump(mode="json")

    assert payload["manifest_version"] == "0.1"
    assert payload["tools"][0]["name"] == "pdf.inspect.document"


def test_file_ref_serializes_explicit_path() -> None:
    ref = FileRef(path=Path("tests/fixtures/simple.pdf"), mime_type="application/pdf")

    assert ref.model_dump(mode="json")["path"] == "tests/fixtures/simple.pdf"
