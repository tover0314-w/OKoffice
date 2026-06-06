"""Tests for Phase 5 sheet patch tools: cells, table, formulas, chart."""

import zipfile
from pathlib import Path

from okoffice.office.sheet_patch import (
    patch_sheet_cells,
    patch_sheet_chart,
    patch_sheet_formulas,
    patch_sheet_table,
)


def _write_patchable_xlsx(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
            '<Override PartName="/xl/tables/table1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml"/>'
            "</Types>",
        )
        z.writestr(
            "_rels/.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        z.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/table" Target="tables/table1.xml"/>'
            "</Relationships>",
        )
        z.writestr(
            "xl/workbook.xml",
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        z.writestr(
            "xl/sharedStrings.xml",
            '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="2" uniqueCount="2">'
            "<si><t>Hello</t></si><si><t>World</t></si></sst>",
        )
        z.writestr(
            "xl/worksheets/sheet1.xml",
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<sheetData>"
            '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1"><v>100</v></c></row>'
            '<row r="2"><c r="A2" t="s"><v>1</v></c><c r="B2"><f>SUM(B1:B5)</f><v>100</v></c></row>'
            "</sheetData></worksheet>",
        )
        z.writestr(
            "xl/worksheets/_rels/sheet1.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/table" Target="../tables/table1.xml"/>'
            "</Relationships>",
        )
        z.writestr(
            "xl/tables/table1.xml",
            '<table xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" displayName="Data" name="Data" ref="A1:B5">'
            '<tableColumns count="2"><tableColumn id="1" name="Col1"/><tableColumn id="2" name="Col2"/></tableColumns>'
            "</table>",
        )


class TestPatchSheetCells:
    def test_patches_cell_value(self, tmp_path: Path) -> None:
        src = tmp_path / "input.xlsx"
        out = tmp_path / "patched.xlsx"
        _write_patchable_xlsx(src)

        result = patch_sheet_cells(
            path=src,
            output_path=out,
            operations=[{"op": "set_value", "sheet": "Sheet1", "cell": "A1", "value": "Updated"}],
        )

        assert result.status == "succeeded"
        assert result.usage["summary"]["cell_patch_count"] == 1

    def test_rejects_non_xlsx(self, tmp_path: Path) -> None:
        src = tmp_path / "input.txt"
        src.write_text("not a workbook")
        out = tmp_path / "out.xlsx"

        result = patch_sheet_cells(path=src, output_path=out, operations=[{"op": "set_value", "sheet": "S", "cell": "A1", "value": "x"}])

        assert result.status == "failed"


class TestPatchSheetTable:
    def test_patches_table_range(self, tmp_path: Path) -> None:
        src = tmp_path / "input.xlsx"
        out = tmp_path / "patched.xlsx"
        _write_patchable_xlsx(src)

        result = patch_sheet_table(
            path=src,
            output_path=out,
            operations=[{"op": "update_range", "table_name": "Data", "range": "A1:C10"}],
        )

        assert result.status == "succeeded"
        assert result.usage["summary"]["table_patch_count"] == 1


class TestPatchSheetFormulas:
    def test_patches_formula(self, tmp_path: Path) -> None:
        src = tmp_path / "input.xlsx"
        out = tmp_path / "patched.xlsx"
        _write_patchable_xlsx(src)

        result = patch_sheet_formulas(
            path=src,
            output_path=out,
            operations=[{"op": "replace_formula", "sheet": "Sheet1", "cell": "B2", "formula": "SUM(B1:B10)"}],
        )

        assert result.status == "succeeded"
        assert result.usage["summary"]["formula_patch_count"] == 1


class TestPatchSheetChart:
    def test_handles_no_charts(self, tmp_path: Path) -> None:
        src = tmp_path / "input.xlsx"
        out = tmp_path / "patched.xlsx"
        _write_patchable_xlsx(src)

        result = patch_sheet_chart(
            path=src,
            output_path=out,
            operations=[{"op": "update_title", "chart_id": "1", "title": "Revenue"}],
        )

        assert result.status == "succeeded"
        assert result.usage["summary"]["chart_patch_count"] == 0
