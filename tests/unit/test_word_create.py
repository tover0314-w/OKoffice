import json
from pathlib import Path

import pytest

DOCUMENT_IR = {
    "title": "Test Document",
    "metadata": {"creator": "Test Author"},
    "sections": [
        {
            "heading": "Introduction",
            "level": 1,
            "paragraphs": ["First paragraph.", "Second paragraph."],
            "tables": [],
        },
        {
            "heading": "Details",
            "level": 2,
            "paragraphs": ["Detail content."],
            "tables": [{"columns": ["Name", "Value"], "rows": [["Alpha", "1"]]}],
        },
    ],
}

MEMO_IR = {
    "to": "John Smith",
    "from": "Jane Doe",
    "date": "2024-01-15",
    "subject": "Test Memo",
    "body": ["This is the first paragraph.", "This is the second."],
    "metadata": {"creator": "Jane Doe"},
}


class TestCreateWordDocument:
    def test_creates_document_from_ir(self, tmp_path: Path) -> None:
        from okoffice.office.word_create import create_word_document

        output = tmp_path / "doc.docx"
        result = create_word_document(output_path=output, document_ir=DOCUMENT_IR)

        assert result.status == "succeeded"
        assert result.tool == "word.create.document"
        assert result.usage["summary"]["paragraph_count"] > 0
        assert result.usage["summary"]["heading_count"] > 0
        assert output.exists()

    def test_creates_document_with_tables(self, tmp_path: Path) -> None:
        from okoffice.office.word_create import create_word_document

        output = tmp_path / "doc.docx"
        result = create_word_document(output_path=output, document_ir=DOCUMENT_IR)

        assert result.status == "succeeded"
        assert result.usage["summary"]["table_count"] > 0

    def test_rejects_non_docx_output(self, tmp_path: Path) -> None:
        from okoffice.office.word_create import create_word_document

        output = tmp_path / "doc.txt"
        result = create_word_document(output_path=output, document_ir=DOCUMENT_IR)

        assert result.status == "failed"


class TestCreateWordMemo:
    def test_creates_memo(self, tmp_path: Path) -> None:
        from okoffice.office.word_create import create_word_memo

        output = tmp_path / "memo.docx"
        result = create_word_memo(output_path=output, memo_ir=MEMO_IR)

        assert result.status == "succeeded"
        assert result.tool == "word.create.memo"
        assert result.usage["summary"]["paragraph_count"] > 0

    def test_memo_includes_header_fields(self, tmp_path: Path) -> None:
        from okoffice.office.word_create import create_word_memo
        from okoffice.office.word_extract import extract_word_text

        output = tmp_path / "memo.docx"
        create_word_memo(output_path=output, memo_ir=MEMO_IR)

        text_result = extract_word_text(output)
        all_text = " ".join(p["text"] for p in text_result.usage["paragraphs"])
        assert "To:" in all_text
        assert "From:" in all_text
