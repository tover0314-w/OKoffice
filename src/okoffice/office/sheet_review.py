"""Heuristic sheet review tools for model quality and number consistency."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from okoffice.office.shared import failed_result, job_id, validation_report_status
from okoffice.office.sheet import FORMULA_CELL_REF_RE, VOLATILE_FORMULA_RE, inspect_sheet_workbook
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport

REVIEW_MODEL_TOOL = "sheet.review.model"
REVIEW_NUMBER_CONSISTENCY_TOOL = "sheet.review.number_consistency"


def review_sheet_model(path: str | Path) -> ToolResult:
    """Analyse spreadsheet model quality heuristically (no model calls)."""
    doc = inspect_sheet_workbook(path)
    if doc.status == "failed":
        return failed_result(REVIEW_MODEL_TOOL, doc.error or OKofficeError(code="inspect_failed", message="Sheet inspect failed."))

    formulas: list[dict[str, Any]] = doc.usage.get("formulas", []) or []
    hardcoded = _hardcoded_literals(formulas)
    volatile = _volatile_formulas(formulas)
    orphans = _orphan_inputs(doc.usage, _formula_refs(formulas))
    depth = _chain_depth(formulas)
    hc, vc = len(hardcoded), len(volatile)

    warnings = []
    if hc: warnings.append(f"Hardcoded literal values found in {hc} formula(s).")
    if vc: warnings.append(f"Volatile functions detected in {vc} formula(s).")

    summary = {"formula_count": len(formulas), "hardcoded_count": hc, "volatile_count": vc, "max_chain_depth": depth, "orphan_input_count": len(orphans)}
    checks = [ValidationCheck(name="format_is_xlsx", status="passed"), ValidationCheck(name="model_reviewed", status="passed", details=summary)]
    if hc: checks.append(ValidationCheck(name="hardcoded_literals_absent", status="warning", details={"hardcoded_count": hc}, message="Formulas contain hardcoded literal values."))
    if vc: checks.append(ValidationCheck(name="volatile_formulas_absent", status="warning", details={"volatile_count": vc}, message="Volatile formula functions were detected."))

    return ToolResult(job_id=job_id(), status="succeeded", tool=REVIEW_MODEL_TOOL,
        validation=ValidationReport(status=validation_report_status(checks), checks=checks, warnings=warnings),
        warnings=warnings, usage={"summary": summary, "model_review": {"hardcoded_in_formulas": hardcoded[:50], "volatile_formulas": volatile[:50], "orphan_inputs": orphans[:50]}},
        next_recommended_tools=["sheet.validation.formulas", "sheet.profile.data", "office.context.build_packet"])


def review_sheet_number_consistency(path: str | Path) -> ToolResult:
    """Check number formatting consistency across sheets."""
    doc = inspect_sheet_workbook(path)
    if doc.status == "failed":
        return failed_result(REVIEW_NUMBER_CONSISTENCY_TOOL, doc.error or OKofficeError(code="inspect_failed", message="Sheet inspect failed."))

    sheets: list[dict[str, Any]] = doc.usage.get("sheets", []) or []
    hidden = [{"name": s.get("name"), "state": s.get("state")} for s in sheets if s.get("hidden")]
    mixed = _mixed_columns(sheets)
    pct = _percentage_columns(sheets)
    hn, mc = len(hidden), len(mixed)

    warnings = []
    if hn: warnings.append(f"Hidden sheets detected: {', '.join(str(h['name']) for h in hidden)}.")
    if mc: warnings.append(f"Mixed format columns detected: {mc}.")

    summary = {"sheet_count": len(sheets), "hidden_sheet_count": hn, "mixed_format_columns": mc, "percentage_columns": len(pct)}
    checks = [ValidationCheck(name="format_is_xlsx", status="passed"), ValidationCheck(name="number_consistency_reviewed", status="passed", details=summary)]
    if hn: checks.append(ValidationCheck(name="hidden_sheets_absent", status="warning", details={"hidden_sheet_count": hn}, message="Hidden sheets were detected."))

    return ToolResult(job_id=job_id(), status="succeeded", tool=REVIEW_NUMBER_CONSISTENCY_TOOL,
        validation=ValidationReport(status=validation_report_status(checks), checks=checks, warnings=warnings),
        warnings=warnings, usage={"summary": summary, "consistency_report": {"hidden_sheets": hidden, "mixed_format_columns": mixed[:50], "percentage_columns": pct[:50]}},
        next_recommended_tools=["sheet.validate.workbook", "sheet.profile.data", "office.context.build_packet"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_number(value: str) -> bool:
    try:
        float(value.replace(",", ""))
        return True
    except ValueError:
        return False


def _hardcoded_literals(formulas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for f in formulas:
        text = str(f.get("formula", ""))
        if not text:
            continue
        stripped = FORMULA_CELL_REF_RE.sub("", text)
        stripped = re.sub(r"[+\-*/^&=(), <>\"']", " ", stripped)
        literals = [m.group(0) for m in re.finditer(r"\b\d+(?:\.\d+)?\b", stripped) if m.group(0) not in {"0", "1"}]
        if literals:
            results.append({"sheet": f.get("sheet", ""), "cell": f.get("cell", ""), "formula": text, "literals": literals})
    return results


def _volatile_formulas(formulas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for f in formulas:
        text = str(f.get("formula", ""))
        funcs = [m.group(1).upper() for m in VOLATILE_FORMULA_RE.finditer(text)]
        if funcs:
            results.append({"sheet": f.get("sheet", ""), "cell": f.get("cell", ""), "formula": text, "volatile_functions": list(dict.fromkeys(funcs))})
    return results


def _formula_refs(formulas: list[dict[str, Any]]) -> set[str]:
    refs: set[str] = set()
    for f in formulas:
        for m in FORMULA_CELL_REF_RE.finditer(str(f.get("formula", ""))):
            ref = m.group(0).replace("$", "").upper()
            if ":" not in ref:
                refs.add(ref)
    return refs


def _orphan_inputs(usage: dict[str, Any], formula_refs: set[str]) -> list[dict[str, Any]]:
    orphans: list[dict[str, Any]] = []
    for sheet in usage.get("sheets", []) or []:
        if sheet.get("hidden"):
            continue
        for row in sheet.get("rows", []) or []:
            if not isinstance(row, list):
                continue
            for val in row:
                v = str(val).strip()
                if v and _is_number(v):
                    orphans.append({"sheet": sheet.get("name", ""), "value": v})
                    break
            if len(orphans) >= 50:
                return orphans
    return orphans


def _chain_depth(formulas: list[dict[str, Any]]) -> int:
    if not formulas:
        return 0
    graph: dict[str, list[str]] = {}
    for f in formulas:
        key = f"{f.get('sheet', '')}!{str(f.get('cell', '')).upper()}"
        graph[key] = [m.group(0).replace("$", "").upper() for m in FORMULA_CELL_REF_RE.finditer(str(f.get("formula", ""))) if ":" not in m.group(0)]

    def depth(cell: str, visited: set[str]) -> int:
        if cell in visited:
            return 0
        visited.add(cell)
        preds = graph.get(cell, [])
        return 1 + max((depth(p, visited.copy()) for p in preds), default=0) if preds else 0

    return max((depth(c, set()) for c in graph), default=0)


def _sheet_rows(sheets: list[dict[str, Any]]) -> list[tuple[str, list[list[Any]]]]:
    result = []
    for s in sheets:
        rows = s.get("rows", [])
        if isinstance(rows, list) and len(rows) >= 2:
            result.append((str(s.get("name", "")), rows))
    return result


def _mixed_columns(sheets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for name, rows in _sheet_rows(sheets):
        max_cols = max((len(r) for r in rows if isinstance(r, list)), default=0)
        for ci in range(max_cols):
            types: set[str] = set()
            for row in rows[1:]:
                if isinstance(row, list) and ci < len(row):
                    v = str(row[ci]).strip()
                    if v:
                        types.add("number" if _is_number(v) else "text")
            if len(types) > 1:
                results.append({"sheet": name, "column_index": ci + 1, "types": sorted(types)})
    return results


def _percentage_columns(sheets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for name, rows in _sheet_rows(sheets):
        max_cols = max((len(r) for r in rows if isinstance(r, list)), default=0)
        for ci in range(max_cols):
            pct, total = 0, 0
            for row in rows[1:]:
                if isinstance(row, list) and ci < len(row):
                    v = str(row[ci]).strip()
                    if v:
                        total += 1
                        if "%" in v:
                            pct += 1
            if total and pct > total * 0.5:
                results.append({"sheet": name, "column_index": ci + 1, "percent_count": pct, "total_count": total})
    return results
