"""Tests for sheet.extract.* tools: formulas, charts, named ranges, comments, pivots."""

import zipfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Shared XLSX fixtures
# ---------------------------------------------------------------------------

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
    '<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
    '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
    '<Override PartName="/xl/comments1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.comments+xml"/>'
    '</Types>'
)

_RELS = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
    '</Relationships>'
)

_WORKBOOK_RELS = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>'
    '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
    '</Relationships>'
)

_WORKBOOK_WITH_NAMES = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/>'
    '<sheet name="Sheet2" sheetId="2" r:id="rId2"/></sheets>'
    '<definedNames><definedName name="MyRange">Sheet1!$A$1:$A$10</definedName></definedNames>'
    '</workbook>'
)

_WORKBOOK_NO_NAMES = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/>'
    '<sheet name="Sheet2" sheetId="2" r:id="rId2"/></sheets>'
    '</workbook>'
)

_SHEET1 = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<sheetData>'
    '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1"><v>100</v></c></row>'
    '<row r="2"><c r="A2"><f>SUM(B1:B5)</f><v>0</v></c></row>'
    '</sheetData></worksheet>'
)

_SHEET2 = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<sheetData>'
    '<row r="1"><c r="A1"><v>42</v></c></row>'
    '</sheetData></worksheet>'
)

_SHARED_STRINGS = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="1" uniqueCount="1">'
    '<si><t>Header</t></si></sst>'
)

_COMMENTS1 = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<comments xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<authors><author>Alice</author></authors>'
    '<commentList>'
    '<comment ref="A1" authorId="0"><text><t>Note on A1</t></text></comment>'
    '</commentList></comments>'
)

_PIVOT_CACHE_DEF = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<pivotCacheDefinition xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" cacheId="1">'
    '<cacheSource type="worksheet">'
    '<worksheetSource ref="A1:B10" sheet="Sheet1"/>'
    '</cacheSource>'
    '<cacheRecords count="10"/>'
    '</pivotCacheDefinition>'
)

_SHEET1_RELS_WITH_COMMENTS = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments" Target="../comments1.xml"/>'
    '</Relationships>'
)

_SHEET1_RELS_EMPTY = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '</Relationships>'
)


def _write_rich_xlsx(path: Path) -> None:
    """Write a minimal XLSX with formulas, named ranges, comments, and pivot cache."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("_rels/.rels", _RELS)
        zf.writestr("xl/workbook.xml", _WORKBOOK_WITH_NAMES)
        zf.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS)
        zf.writestr("xl/worksheets/sheet1.xml", _SHEET1)
        zf.writestr("xl/worksheets/sheet2.xml", _SHEET2)
        zf.writestr("xl/sharedStrings.xml", _SHARED_STRINGS)
        zf.writestr("xl/comments1.xml", _COMMENTS1)
        zf.writestr("xl/worksheets/_rels/sheet1.xml.rels", _SHEET1_RELS_WITH_COMMENTS)
        zf.writestr("xl/worksheets/_rels/sheet2.xml.rels", _SHEET1_RELS_EMPTY)
        zf.writestr("xl/pivotCache/pivotCacheDefinition1.xml", _PIVOT_CACHE_DEF)


def _write_xlsx_no_named_ranges(path: Path) -> None:
    """Write an XLSX without defined names."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("_rels/.rels", _RELS)
        zf.writestr("xl/workbook.xml", _WORKBOOK_NO_NAMES)
        zf.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS)
        zf.writestr("xl/worksheets/sheet1.xml", _SHEET1)
        zf.writestr("xl/worksheets/sheet2.xml", _SHEET2)
        zf.writestr("xl/sharedStrings.xml", _SHARED_STRINGS)
        zf.writestr("xl/worksheets/_rels/sheet1.xml.rels", _SHEET1_RELS_EMPTY)
        zf.writestr("xl/worksheets/_rels/sheet2.xml.rels", _SHEET1_RELS_EMPTY)


def _write_xlsx_no_comments(path: Path) -> None:
    """Write an XLSX without comments."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("_rels/.rels", _RELS)
        zf.writestr("xl/workbook.xml", _WORKBOOK_WITH_NAMES)
        zf.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS)
        zf.writestr("xl/worksheets/sheet1.xml", _SHEET1)
        zf.writestr("xl/worksheets/sheet2.xml", _SHEET2)
        zf.writestr("xl/sharedStrings.xml", _SHARED_STRINGS)
        zf.writestr("xl/worksheets/_rels/sheet1.xml.rels", _SHEET1_RELS_EMPTY)
        zf.writestr("xl/worksheets/_rels/sheet2.xml.rels", _SHEET1_RELS_EMPTY)


def _write_xlsx_no_pivots(path: Path) -> None:
    """Write an XLSX without pivot cache parts."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("_rels/.rels", _RELS)
        zf.writestr("xl/workbook.xml", _WORKBOOK_WITH_NAMES)
        zf.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS)
        zf.writestr("xl/worksheets/sheet1.xml", _SHEET1)
        zf.writestr("xl/worksheets/sheet2.xml", _SHEET2)
        zf.writestr("xl/sharedStrings.xml", _SHARED_STRINGS)
        zf.writestr("xl/worksheets/_rels/sheet1.xml.rels", _SHEET1_RELS_WITH_COMMENTS)
        zf.writestr("xl/worksheets/_rels/sheet2.xml.rels", _SHEET1_RELS_EMPTY)


# ---------------------------------------------------------------------------
# TestExtractFormulas
# ---------------------------------------------------------------------------

class TestExtractFormulas:
    def test_extracts_formulas(self, tmp_path: Path) -> None:
        from okoffice.office.sheet_extract import extract_sheet_formulas

        xlsx_path = tmp_path / "test.xlsx"
        _write_rich_xlsx(xlsx_path)
        result = extract_sheet_formulas(xlsx_path)
        assert result.status == "succeeded"
        assert result.tool == "sheet.extract.formulas"
        summary = result.usage["summary"]
        assert summary["formula_count"] > 0
        formulas = result.usage["formulas"]
        assert any("SUM" in f["formula"] for f in formulas)

    def test_rejects_non_xlsx(self, tmp_path: Path) -> None:
        from okoffice.office.sheet_extract import extract_sheet_formulas

        bad_path = tmp_path / "test.pdf"
        bad_path.write_text("not an xlsx", encoding="utf-8")
        result = extract_sheet_formulas(bad_path)
        assert result.status == "failed"


# ---------------------------------------------------------------------------
# TestExtractCharts
# ---------------------------------------------------------------------------

class TestExtractCharts:
    def test_extracts_charts(self, tmp_path: Path) -> None:
        from okoffice.office.sheet_extract import extract_sheet_charts

        xlsx_path = tmp_path / "test.xlsx"
        _write_rich_xlsx(xlsx_path)
        result = extract_sheet_charts(xlsx_path)
        assert result.status == "succeeded"
        assert result.tool == "sheet.extract.charts"
        assert "chart_count" in result.usage["summary"]

    def test_rejects_non_xlsx(self, tmp_path: Path) -> None:
        from okoffice.office.sheet_extract import extract_sheet_charts

        bad_path = tmp_path / "test.txt"
        bad_path.write_text("hello", encoding="utf-8")
        result = extract_sheet_charts(bad_path)
        assert result.status == "failed"


# ---------------------------------------------------------------------------
# TestExtractNamedRanges
# ---------------------------------------------------------------------------

class TestExtractNamedRanges:
    def test_extracts_named_ranges(self, tmp_path: Path) -> None:
        from okoffice.office.sheet_extract import extract_sheet_named_ranges

        xlsx_path = tmp_path / "test.xlsx"
        _write_rich_xlsx(xlsx_path)
        result = extract_sheet_named_ranges(xlsx_path)
        assert result.status == "succeeded"
        assert result.tool == "sheet.extract.named_ranges"
        summary = result.usage["summary"]
        assert summary["named_range_count"] > 0
        ranges = result.usage["named_ranges"]
        assert any(r.get("name") == "MyRange" for r in ranges)

    def test_handles_no_named_ranges(self, tmp_path: Path) -> None:
        from okoffice.office.sheet_extract import extract_sheet_named_ranges

        xlsx_path = tmp_path / "no_names.xlsx"
        _write_xlsx_no_named_ranges(xlsx_path)
        result = extract_sheet_named_ranges(xlsx_path)
        assert result.status == "succeeded"
        assert result.usage["summary"]["named_range_count"] == 0


# ---------------------------------------------------------------------------
# TestExtractComments
# ---------------------------------------------------------------------------

class TestExtractComments:
    def test_extracts_comments(self, tmp_path: Path) -> None:
        from okoffice.office.sheet_extract import extract_sheet_comments

        xlsx_path = tmp_path / "test.xlsx"
        _write_rich_xlsx(xlsx_path)
        result = extract_sheet_comments(xlsx_path)
        assert result.status == "succeeded"
        assert result.tool == "sheet.extract.comments"
        comments = result.usage["comments"]
        assert result.usage["summary"]["comment_count"] > 0
        assert any(c["author"] == "Alice" for c in comments)

    def test_handles_no_comments(self, tmp_path: Path) -> None:
        from okoffice.office.sheet_extract import extract_sheet_comments

        xlsx_path = tmp_path / "no_comments.xlsx"
        _write_xlsx_no_comments(xlsx_path)
        result = extract_sheet_comments(xlsx_path)
        assert result.status == "succeeded"
        assert result.usage["summary"]["comment_count"] == 0


# ---------------------------------------------------------------------------
# TestExtractPivots
# ---------------------------------------------------------------------------

class TestExtractPivots:
    def test_extracts_pivots(self, tmp_path: Path) -> None:
        from okoffice.office.sheet_extract import extract_sheet_pivots

        xlsx_path = tmp_path / "test.xlsx"
        _write_rich_xlsx(xlsx_path)
        result = extract_sheet_pivots(xlsx_path)
        assert result.status == "succeeded"
        assert result.tool == "sheet.extract.pivots"
        assert result.usage["summary"]["pivot_cache_count"] > 0
        pivots = result.usage["pivots"]
        assert any(p.get("cache_id") for p in pivots)

    def test_handles_no_pivots(self, tmp_path: Path) -> None:
        from okoffice.office.sheet_extract import extract_sheet_pivots

        xlsx_path = tmp_path / "no_pivots.xlsx"
        _write_xlsx_no_pivots(xlsx_path)
        result = extract_sheet_pivots(xlsx_path)
        assert result.status == "succeeded"
        assert result.usage["summary"]["pivot_cache_count"] == 0
