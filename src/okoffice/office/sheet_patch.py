from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from okoffice.artifacts.store import build_artifact
from okoffice.office.ooxml import read_xml, zip_names
from okoffice.office.shared import failed_result, job_id
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport
from okoffice.security.paths import resolve_input_path, resolve_output_path

CELL_TOOL = "sheet.patch.cells"
TABLE_TOOL = "sheet.patch.table"
FORMULA_TOOL = "sheet.patch.formulas"
CHART_TOOL = "sheet.patch.chart"

SS_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
TAG = f"{{{SS_NS}}}"
CHART_NS = "http://schemas.openxmlformats.org/drawingml/2006/chart"
CTAG = f"{{{CHART_NS}}}"
CELL_REF_RE = re.compile(r"^([A-Z]+)([0-9]+)$", re.IGNORECASE)


def _preflight(path: str | Path, output_path: str | Path, tool: str) -> tuple[Path, Path]:
    input_file = resolve_input_path(path)
    output_file = resolve_output_path(output_path)
    if input_file == output_file:
        raise OKofficeException("invalid_input", f"{tool} writes to a new output_path and never mutates the input workbook.", details={"input_path": input_file.as_posix(), "output_path": output_file.as_posix()})
    if output_file.suffix.lower() != ".xlsx":
        raise OKofficeException("unsupported_file_type", f"{tool} writes .xlsx output files.", details={"output_path": output_file.as_posix()})
    return input_file, output_file


def _parse_cell_ref(ref: str) -> tuple[int, int] | None:
    m = CELL_REF_RE.match(ref)
    if not m:
        return None
    col, row = m.groups()
    num = 0
    for ch in col.upper():
        num = num * 26 + (ord(ch) - ord("A") + 1)
    return int(row), num


def _unsafe(name: str) -> bool:
    n = name.replace("\\", "/")
    return n.startswith("/") or n.startswith("../") or "/../" in n


def _sheet_idx(member: str) -> int:
    digits = re.sub(r"\D", "", member.rsplit("/", 1)[-1].replace(".xml", ""))
    return int(digits) if digits else 1


def _sheet_name(wb_root: ElementTree.Element | None, idx: int) -> str:
    if wb_root is None:
        return f"Sheet{idx}"
    sheets = wb_root.findall(f"{TAG}sheets/{TAG}sheet")
    return str(sheets[idx - 1].get("name") or f"Sheet{idx}") if 1 <= idx <= len(sheets) else f"Sheet{idx}"


def _build_result(tool: str, inp: Path, out: Path, ops: list[dict[str, Any]], summary: dict[str, Any]) -> ToolResult:
    jid = job_id()
    return ToolResult(job_id=jid, status="succeeded", tool=tool, artifacts=[build_artifact(out, source_tool=tool)],
        validation=ValidationReport(status="passed", checks=[
            ValidationCheck(name="input_path_safe", status="passed", details={"path": inp.as_posix()}),
            ValidationCheck(name="output_path_distinct", status="passed", details={"path": out.as_posix()}),
            ValidationCheck(name="operations_applied", status="passed", details={"operation_count": len(ops), **summary}),
        ]),
        usage={"summary": summary, "patch_transaction": {
            "transaction_id": f"patch_{jid.removeprefix('job_')}", "input_path": inp.as_posix(),
            "output_path": out.as_posix(), "mutates_inputs": False, "operation_count": len(ops),
            "operations": ops, "rollback": {"strategy": "discard_output", "input_preserved": True},
        }},
        next_recommended_tools=["sheet.inspect.workbook", "sheet.validate.workbook"])


def _wrap(tool: str, fn):
    try:
        return fn()
    except OKofficeException as exc:
        return failed_result(tool, exc.to_error())
    except (zipfile.BadZipFile, ValueError, ElementTree.ParseError) as exc:
        return failed_result(tool, OKofficeError(code="invalid_input", message=str(exc)))


def _validate_ops(ops: list[dict[str, Any]], label: str) -> None:
    if not isinstance(ops, list) or not ops:
        raise OKofficeException("invalid_input", f"{label} operations must be a non-empty list.")


def _require(op: dict, key: str, index: int, label: str) -> str:
    val = str(op.get(key) or "")
    if not val:
        raise OKofficeException("invalid_input", f"{label} patch operation {index} requires {key}.")
    return val


def _op_kind(op: dict, index: int, expected: str, label: str) -> str:
    kind = str(op.get("op") or "")
    if kind != expected:
        raise OKofficeException("invalid_input", f"Unsupported {label} patch operation: {kind or '<missing>'}")
    return kind


def patch_sheet_cells(*, path: str | Path, output_path: str | Path, operations: list[dict[str, Any]]) -> ToolResult:
    def _run():
        inp, out = _preflight(path, output_path, CELL_TOOL)
        _validate_ops(operations, "Cell")
        norm = _norm_cell_ops(operations)
        summary = _write_cells(inp, out, norm)
        return _build_result(CELL_TOOL, inp, out, norm, summary)
    return _wrap(CELL_TOOL, _run)


def _norm_cell_ops(ops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for i, op in enumerate(ops, 1):
        if not isinstance(op, dict):
            raise OKofficeException("invalid_input", f"Cell patch operation {i} must be an object.")
        _op_kind(op, i, "set_value", "cell")
        sheet = _require(op, "sheet", i, "Cell")
        cell = str(op.get("cell") or "").upper()
        if not cell or _parse_cell_ref(cell) is None:
            raise OKofficeException("invalid_input", f"Cell patch operation {i} has invalid cell ref: {cell}")
        result.append({"op": "set_value", "sheet": sheet, "cell": cell, "value": str(op.get("value") if op.get("value") is not None else "")})
    return result


def _read_sst(archive: zipfile.ZipFile, names: set[str]) -> list[str]:
    if "xl/sharedStrings.xml" not in names:
        return []
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    return ["".join(t.text or "" for t in si.findall(f".//{TAG}t")).strip() for si in root.findall(f"{TAG}si")]


def _write_cells(inp: Path, out: Path, ops: list[dict[str, Any]]) -> dict[str, Any]:
    out.parent.mkdir(parents=True, exist_ok=True)
    names = zip_names(inp)
    wb = read_xml(inp, "xl/workbook.xml")
    count, sheets = 0, set[str]()

    with zipfile.ZipFile(inp) as src, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as tgt:
        sst = _read_sst(src, names)
        for info in src.infolist():
            name = info.filename.replace("\\", "/")
            if _unsafe(name):
                raise OKofficeException("unsafe_input_rejected", "Workbook contains unsafe ZIP entries.")
            data = src.read(info.filename)
            if name == "xl/sharedStrings.xml":
                data = _patch_sst(data, ops, sst)
            elif name.startswith("xl/worksheets/sheet") and name.endswith(".xml"):
                sn = _sheet_name(wb, _sheet_idx(name))
                matching = [o for o in ops if o["sheet"] == sn]
                if matching:
                    data, c = _patch_ws_cells(data, matching, sst)
                    count += c
                    sheets.add(sn)
            tgt.writestr(name, data)
    return {"cell_patch_count": count, "sheet_count_affected": len(sheets)}


def _patch_sst(data: bytes, ops: list[dict[str, Any]], sst: list[str]) -> bytes:
    root = ElementTree.fromstring(data)
    for op in ops:
        v = op["value"]
        try:
            float(v)
            continue
        except (ValueError, TypeError):
            pass
        if v not in sst:
            si = ElementTree.SubElement(root, f"{TAG}si")
            t = ElementTree.SubElement(si, f"{TAG}t")
            t.text = v
            sst.append(v)
    count_val = str(len(sst))
    for attr in ("count", "uniqueCount"):
        root.set(attr, count_val)
    return ElementTree.tostring(root, encoding="unicode").encode("utf-8")


def _patch_ws_cells(data: bytes, ops: list[dict[str, Any]], sst: list[str]) -> tuple[bytes, int]:
    root = ElementTree.fromstring(data)
    sd = root.find(f"{TAG}sheetData")
    if sd is None:
        return data, 0
    count = 0
    for op in ops:
        parsed = _parse_cell_ref(op["cell"])
        row_num = parsed[0] if parsed else 1
        row_el = next((r for r in sd.findall(f"{TAG}row") if r.get("r") == str(row_num)), None)
        if row_el is None:
            row_el = ElementTree.SubElement(sd, f"{TAG}row")
            row_el.set("r", str(row_num))
        cell_el = next((c for c in row_el.findall(f"{TAG}c") if c.get("r") == op["cell"]), None)
        if cell_el is None:
            cell_el = ElementTree.SubElement(row_el, f"{TAG}c")
            cell_el.set("r", op["cell"])
        v = op["value"]
        is_num = False
        try:
            float(v)
            is_num = True
        except (ValueError, TypeError):
            pass
        v_el = cell_el.find(f"{TAG}v")
        if v_el is None:
            v_el = ElementTree.SubElement(cell_el, f"{TAG}v")
        if is_num:
            cell_el.attrib.pop("t", None)
            f_el = cell_el.find(f"{TAG}f")
            if f_el is not None:
                cell_el.remove(f_el)
            v_el.text = v
        else:
            cell_el.set("t", "s")
            idx = sst.index(v) if v in sst else len(sst) - 1
            v_el.text = str(idx)
        count += 1
    return ElementTree.tostring(root, encoding="unicode").encode("utf-8"), count


def patch_sheet_table(*, path: str | Path, output_path: str | Path, operations: list[dict[str, Any]]) -> ToolResult:
    def _run():
        inp, out = _preflight(path, output_path, TABLE_TOOL)
        _validate_ops(operations, "Table")
        norm = _norm_table_ops(operations)
        summary = _write_tables(inp, out, norm)
        return _build_result(TABLE_TOOL, inp, out, norm, summary)
    return _wrap(TABLE_TOOL, _run)


def _norm_table_ops(ops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for i, op in enumerate(ops, 1):
        if not isinstance(op, dict):
            raise OKofficeException("invalid_input", f"Table patch operation {i} must be an object.")
        _op_kind(op, i, "update_range", "table")
        name = _require(op, "table_name", i, "Table")
        rng = _require(op, "range", i, "Table")
        result.append({"op": "update_range", "table_name": name, "range": rng})
    return result


def _write_tables(inp: Path, out: Path, ops: list[dict[str, Any]]) -> dict[str, Any]:
    out.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(inp) as src, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as tgt:
        for info in src.infolist():
            name = info.filename.replace("\\", "/")
            if _unsafe(name):
                raise OKofficeException("unsafe_input_rejected", "Workbook contains unsafe ZIP entries.")
            data = src.read(info.filename)
            if name.startswith("xl/tables/") and name.endswith(".xml"):
                root = ElementTree.fromstring(data)
                tname = str(root.get("displayName") or root.get("name") or "")
                for op in ops:
                    if op["table_name"] == tname:
                        root.set("ref", op["range"])
                        count += 1
                data = ElementTree.tostring(root, encoding="unicode").encode("utf-8")
            tgt.writestr(name, data)
    return {"table_patch_count": count}


def patch_sheet_formulas(*, path: str | Path, output_path: str | Path, operations: list[dict[str, Any]]) -> ToolResult:
    def _run():
        inp, out = _preflight(path, output_path, FORMULA_TOOL)
        _validate_ops(operations, "Formula")
        norm = _norm_formula_ops(operations)
        summary = _write_formulas(inp, out, norm)
        return _build_result(FORMULA_TOOL, inp, out, norm, summary)
    return _wrap(FORMULA_TOOL, _run)


def _norm_formula_ops(ops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for i, op in enumerate(ops, 1):
        if not isinstance(op, dict):
            raise OKofficeException("invalid_input", f"Formula patch operation {i} must be an object.")
        _op_kind(op, i, "replace_formula", "formula")
        sheet = _require(op, "sheet", i, "Formula")
        cell = str(op.get("cell") or "").upper()
        formula = _require(op, "formula", i, "Formula")
        if not cell or _parse_cell_ref(cell) is None:
            raise OKofficeException("invalid_input", f"Formula patch operation {i} has invalid cell ref.")
        result.append({"op": "replace_formula", "sheet": sheet, "cell": cell, "formula": formula})
    return result


def _write_formulas(inp: Path, out: Path, ops: list[dict[str, Any]]) -> dict[str, Any]:
    out.parent.mkdir(parents=True, exist_ok=True)
    wb = read_xml(inp, "xl/workbook.xml")
    count = 0
    with zipfile.ZipFile(inp) as src, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as tgt:
        for info in src.infolist():
            name = info.filename.replace("\\", "/")
            if _unsafe(name):
                raise OKofficeException("unsafe_input_rejected", "Workbook contains unsafe ZIP entries.")
            data = src.read(info.filename)
            if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"):
                sn = _sheet_name(wb, _sheet_idx(name))
                matching = [o for o in ops if o["sheet"] == sn]
                if matching:
                    root = ElementTree.fromstring(data)
                    c = _apply_formula_patches(root, matching)
                    count += c
                    data = ElementTree.tostring(root, encoding="unicode").encode("utf-8")
            tgt.writestr(name, data)
    return {"formula_patch_count": count}


def _apply_formula_patches(root: ElementTree.Element, ops: list[dict[str, Any]]) -> int:
    count = 0
    for row in root.findall(f".//{TAG}sheetData/{TAG}row"):
        for cell in row.findall(f"{TAG}c"):
            ref = str(cell.get("r") or "")
            for op in ops:
                if op["cell"] == ref:
                    f_el = cell.find(f"{TAG}f")
                    if f_el is None:
                        f_el = ElementTree.SubElement(cell, f"{TAG}f")
                    f_el.text = op["formula"]
                    count += 1
    return count


def patch_sheet_chart(*, path: str | Path, output_path: str | Path, operations: list[dict[str, Any]]) -> ToolResult:
    def _run():
        inp, out = _preflight(path, output_path, CHART_TOOL)
        _validate_ops(operations, "Chart")
        norm = _norm_chart_ops(operations)
        summary = _write_charts(inp, out, norm)
        return _build_result(CHART_TOOL, inp, out, norm, summary)
    return _wrap(CHART_TOOL, _run)


def _norm_chart_ops(ops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for i, op in enumerate(ops, 1):
        if not isinstance(op, dict):
            raise OKofficeException("invalid_input", f"Chart patch operation {i} must be an object.")
        _op_kind(op, i, "update_title", "chart")
        cid = _require(op, "chart_id", i, "Chart")
        title = _require(op, "title", i, "Chart")
        result.append({"op": "update_title", "chart_id": cid, "title": title})
    return result


def _write_charts(inp: Path, out: Path, ops: list[dict[str, Any]]) -> dict[str, Any]:
    out.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(inp) as src, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as tgt:
        for info in src.infolist():
            name = info.filename.replace("\\", "/")
            if _unsafe(name):
                raise OKofficeException("unsafe_input_rejected", "Workbook contains unsafe ZIP entries.")
            data = src.read(info.filename)
            if name.startswith("xl/charts/chart") and name.endswith(".xml"):
                cid = re.sub(r"\D", "", name.rsplit("/", 1)[-1].replace(".xml", "")) or name
                matching = [o for o in ops if o["chart_id"] == cid]
                if matching:
                    root = ElementTree.fromstring(data)
                    count += _apply_chart_title(root, matching)
                    data = ElementTree.tostring(root, encoding="unicode").encode("utf-8")
            tgt.writestr(name, data)
    return {"chart_patch_count": count}


def _ensure(parent: ElementTree.Element, tag: str) -> ElementTree.Element:
    el = parent.find(tag)
    if el is None:
        el = ElementTree.SubElement(parent, tag)
    return el


def _apply_chart_title(root: ElementTree.Element, ops: list[dict[str, Any]]) -> int:
    count = 0
    for op in ops:
        title_el = root.find(f".//{CTAG}title")
        if title_el is None:
            chart_el = root.find(f".//{CTAG}chart")
            if chart_el is None:
                continue
            title_el = ElementTree.SubElement(chart_el, f"{CTAG}title")
        t = _ensure(_ensure(_ensure(_ensure(_ensure(title_el, f"{CTAG}tx"), f"{CTAG}rich"), f"{CTAG}bodyPr"), f"{CTAG}p"), f"{CTAG}r")
        t_el = _ensure(t, f"{CTAG}t")
        t_el.text = op["title"]
        count += 1
    return count
