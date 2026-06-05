import json
import zipfile
from pathlib import Path

from typer.testing import CliRunner


def test_word_inspect_document_reports_docx_structure(tmp_path: Path) -> None:
    from agentpdf.office.word import inspect_word_document

    path = tmp_path / "memo.docx"
    _write_docx_fixture(path)

    result = inspect_word_document(path)

    assert result.status == "succeeded"
    assert result.tool == "word.inspect.document"
    assert result.validation is not None
    assert result.validation.status == "warning"

    summary = result.usage["summary"]
    assert summary["paragraph_count"] == 4
    assert summary["heading_count"] == 2
    assert summary["table_count"] == 1
    assert summary["comment_count"] == 1
    assert summary["field_count"] == 1
    assert summary["tracked_change_count"] == 1
    assert summary["section_count"] == 1
    assert summary["style_count"] >= 3

    assert result.usage["metadata"]["title"] == "Renewal Memo"
    assert result.usage["metadata"]["creator"] == "okoffice tests"
    assert result.usage["package"]["has_external_relationships"] is True
    assert result.usage["layout"]["rendered_layout_claimed"] is False
    assert "External Word relationship targets were detected." in result.warnings

    heading = result.usage["headings"][0]
    assert heading["text"] == "Renewal Risk"
    assert heading["locator"]["kind"] == "word"
    assert heading["locator"]["paragraph_index"] == 1
    assert heading["style"] == "Heading 1"

    table = result.usage["tables"][0]
    assert table["row_count"] == 2
    assert table["column_count"] == 2
    assert table["cells"][1][1]["text"] == "High"
    assert table["locator"]["kind"] == "word"

    comment = result.usage["comments"][0]
    assert comment["comment_id"] == "0"
    assert comment["author"] == "Analyst"
    assert comment["text"] == "Needs finance review."


def test_word_inspect_document_rejects_non_docx_zip(tmp_path: Path) -> None:
    from agentpdf.office.word import inspect_word_document

    path = tmp_path / "bad.docx"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")

    result = inspect_word_document(path)

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "unsupported_file_type"


def test_okoffice_word_inspect_cli_returns_tool_result_json(tmp_path: Path) -> None:
    from okoffice.cli.main import app

    path = tmp_path / "memo.docx"
    _write_docx_fixture(path)

    result = CliRunner().invoke(app, ["word", "inspect", str(path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "word.inspect.document"
    assert payload["usage"]["summary"]["heading_count"] == 2
    assert payload["usage"]["paragraphs"][0]["locator"]["kind"] == "word"


def test_word_inspect_document_runs_through_rest_api(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from agentpdf.api.app import create_app

    path = tmp_path / "memo.docx"
    _write_docx_fixture(path)

    response = TestClient(create_app()).post(
        "/v1/tools/word.inspect.document/run",
        json={"path": str(path)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool"] == "word.inspect.document"
    assert payload["usage"]["summary"]["table_count"] == 1


def test_word_inspect_document_runs_through_mcp_function(tmp_path: Path) -> None:
    from agentpdf.mcp.server import word_inspect_document

    path = tmp_path / "memo.docx"
    _write_docx_fixture(path)

    payload = json.loads(word_inspect_document(str(path)))

    assert payload["tool"] == "word.inspect.document"
    assert payload["status"] == "succeeded"
    assert payload["usage"]["summary"]["comment_count"] == 1


def test_word_inspect_document_runs_through_workflow_runner(tmp_path: Path) -> None:
    from agentpdf.workflows.runner import run_workflow

    path = tmp_path / "memo.docx"
    _write_docx_fixture(path)

    result = run_workflow(
        {
            "steps": [
                {
                    "tool": "word.inspect.document",
                    "input": {"path": str(path)},
                }
            ]
        }
    )

    assert result.status == "succeeded"
    step = result.usage["workflow_run"]["step_results"][0]
    assert step["tool"] == "word.inspect.document"
    assert step["status"] == "succeeded"
    assert "office.context.build_packet" in step["next_recommended_tools"]


def _write_docx_fixture(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", _document_xml())
        archive.writestr("word/styles.xml", _styles_xml())
        archive.writestr("word/comments.xml", _comments_xml())
        archive.writestr("word/_rels/document.xml.rels", _relationships_xml())
        archive.writestr("docProps/core.xml", _core_xml())


def _document_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p w:rsidR="001">
      <w:pPr><w:pStyle w:val="Title"/></w:pPr>
      <w:r><w:t>Renewal Memo</w:t></w:r>
    </w:p>
    <w:p>
      <w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
      <w:r><w:t>Renewal Risk</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t>Renewal risk is concentrated in enterprise accounts.</w:t></w:r>
      <w:commentRangeStart w:id="0"/>
      <w:r><w:commentReference w:id="0"/></w:r>
      <w:fldChar w:fldCharType="begin"/>
      <w:r><w:instrText> DATE </w:instrText></w:r>
      <w:ins w:id="1"><w:r><w:t>Updated evidence.</w:t></w:r></w:ins>
    </w:p>
    <w:tbl>
      <w:tr>
        <w:tc><w:p><w:r><w:t>Metric</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>Risk</w:t></w:r></w:p></w:tc>
      </w:tr>
      <w:tr>
        <w:tc><w:p><w:r><w:t>Renewal</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>High</w:t></w:r></w:p></w:tc>
      </w:tr>
    </w:tbl>
    <w:p>
      <w:pPr><w:sectPr><w:pgSz w:w="12240" w:h="15840"/></w:sectPr></w:pPr>
    </w:p>
  </w:body>
</w:document>
"""


def _styles_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/></w:style>
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="Heading 1"/></w:style>
  <w:style w:type="paragraph" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
</w:styles>
"""


def _comments_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:comment w:id="0" w:author="Analyst">
    <w:p><w:r><w:t>Needs finance review.</w:t></w:r></w:p>
  </w:comment>
</w:comments>
"""


def _relationships_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="https://example.com" TargetMode="External"/>
</Relationships>
"""


def _core_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <dc:title>Renewal Memo</dc:title>
  <dc:creator>okoffice tests</dc:creator>
</cp:coreProperties>
"""
