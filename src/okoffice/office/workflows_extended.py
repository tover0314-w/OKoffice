from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

from okoffice.office.deck_patch import apply_deck_patch
from okoffice.office.inspect import inspect_office_file
from okoffice.office.office_patch import SUPPORTED_OPS, plan_office_patch, verify_office_patch
from okoffice.office.shared import failed_result, job_id
from okoffice.office.sheet_patch import patch_sheet_cells, patch_sheet_formulas, patch_sheet_table
from okoffice.office.word_patch import apply_word_patch
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport
from okoffice.security.paths import resolve_input_path, resolve_output_path

REVIEW_PATCH_TOOL = "office.workflow.review_and_patch"
REDACTION_TOOL = "office.workflow.redaction_packet"
GRAPH_TOOL = "office.bundle.graph"
_XML_NS = {
    "docx": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "xlsx": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "pptx": "http://schemas.openxmlformats.org/drawingml/2006/main",
}


def review_and_patch_workflow(*, path: str | Path, output_path: str | Path,
                              operations: list[dict[str, Any]]) -> ToolResult:
    """Full workflow: inspect -> plan -> apply patch -> validate."""
    try:
        resolved = resolve_input_path(path)
        output = resolve_output_path(output_path)
    except OKofficeException as exc:
        return failed_result(REVIEW_PATCH_TOOL, exc.to_error())
    inspect_result = inspect_office_file(resolved)
    if inspect_result.status == "failed":
        return failed_result(REVIEW_PATCH_TOOL, inspect_result.error or OKofficeError(code="inspect_failed", message="Workflow inspect step failed."))
    fmt = str(inspect_result.usage["format"]["detected_format"])
    allowed = SUPPORTED_OPS.get(fmt)
    if allowed is None:
        return failed_result(REVIEW_PATCH_TOOL, OKofficeError(code="unsupported_file_type", message=f"Patch not supported for format: {fmt}"))
    plan_result = plan_office_patch(path=resolved, operations=operations)
    if plan_result.status == "failed":
        return failed_result(REVIEW_PATCH_TOOL, plan_result.error or OKofficeError(code="plan_failed", message="Patch planning step failed."))
    valid_ops = [op for op in operations if str(op.get("op") or "") in allowed]
    if not valid_ops:
        return failed_result(REVIEW_PATCH_TOOL, OKofficeError(code="invalid_input", message="No supported operations for the detected format."))
    patch_result = _apply_format_patch(fmt, resolved, output, valid_ops)
    if patch_result.status == "failed":
        return failed_result(REVIEW_PATCH_TOOL, patch_result.error or OKofficeError(code="patch_failed", message="Patch application step failed."))
    verify_result = verify_office_patch(input_path=resolved, output_path=output)
    all_warnings = _dedupe([w for r in [inspect_result, plan_result, patch_result, verify_result] for w in r.warnings])
    return ToolResult(
        job_id=job_id(), status="succeeded", tool=REVIEW_PATCH_TOOL, artifacts=patch_result.artifacts,
        validation=ValidationReport(status="passed" if verify_result.status == "succeeded" else "warning", checks=[
            ValidationCheck(name="inspect", status="passed", details={"format": fmt}),
            ValidationCheck(name="plan", status="passed", details={"operation_count": len(valid_ops)}),
            ValidationCheck(name="patch", status="passed" if patch_result.status == "succeeded" else "failed", details={"operation_count": len(valid_ops)}),
            ValidationCheck(name="verify", status="passed" if verify_result.status == "succeeded" else "warning", details={"output_path": output.as_posix()}),
        ], warnings=all_warnings), warnings=all_warnings,
        usage={"summary": {"format": fmt, "operation_count": len(valid_ops), "patch_status": patch_result.status, "validation_status": verify_result.status},
               "workflow": {"inspect": _step(inspect_result), "plan": _step(plan_result), "patch": _step(patch_result), "validate": _step(verify_result)}},
        next_recommended_tools=["office.patch.verify", "office.bundle.export"])


def build_redaction_packet(*, path: str | Path, search_terms: list[str]) -> ToolResult:
    """Build a redaction-ready packet from cross-format text scanning."""
    try:
        resolved = resolve_input_path(path)
    except OKofficeException as exc:
        return failed_result(REDACTION_TOOL, exc.to_error())
    inspect_result = inspect_office_file(resolved)
    if inspect_result.status == "failed":
        return failed_result(REDACTION_TOOL, inspect_result.error or OKofficeError(code="inspect_failed", message="Redaction packet inspect failed."))
    fmt = str(inspect_result.usage["format"]["detected_format"])
    if not isinstance(search_terms, list) or not search_terms:
        raise OKofficeException("invalid_input", "search_terms must be a non-empty list of strings.")
    text = _extract_text(resolved, fmt)
    terms_data: list[dict[str, Any]] = []
    total = 0
    for term in search_terms:
        t = str(term)
        occ = text.lower().count(t.lower())
        total += occ
        terms_data.append({"term": t, "occurrences": occ, "locations": _find_locations(text, t)})
    return ToolResult(
        job_id=job_id(), status="succeeded", tool=REDACTION_TOOL,
        validation=ValidationReport(status="passed", checks=[
            ValidationCheck(name="format_detected", status="passed", details={"detected_format": fmt}),
            ValidationCheck(name="terms_scanned", status="passed", details={"term_count": len(search_terms), "occurrence_count": total}),
        ]),
        usage={"summary": {"term_count": len(search_terms), "occurrence_count": total, "detected_format": fmt},
               "redaction_packet": {"terms": terms_data, "source_path": resolved.as_posix(), "detected_format": fmt}},
        next_recommended_tools=["office.patch.plan", "office.workflow.review_and_patch"])


def build_artifact_graph(*, artifact_paths: list[str | Path]) -> ToolResult:
    """Create an artifact lineage graph from multi-format outputs."""
    if not artifact_paths:
        return failed_result(GRAPH_TOOL, OKofficeError(code="invalid_input", message="artifact_paths must be a non-empty list."))
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    inspected: list[tuple[int, ToolResult]] = []
    for idx, ap in enumerate(artifact_paths):
        try:
            resolved = resolve_input_path(ap)
        except OKofficeException:
            continue
        ir = inspect_office_file(resolved)
        if ir.status != "succeeded":
            continue
        fmt = str(ir.usage["format"]["detected_format"])
        nodes.append({"id": f"artifact_{idx}", "path": resolved.as_posix(), "format": fmt})
        inspected.append((idx, ir))
    for i in range(len(inspected) - 1):
        edges.append({"source": f"artifact_{inspected[i][0]}", "target": f"artifact_{inspected[i + 1][0]}", "type": "sequential"})
    for i, (ia, ra) in enumerate(inspected):
        for j, (ib, rb) in enumerate(inspected):
            if i >= j:
                continue
            fa, fb = str(ra.usage["format"]["detected_format"]), str(rb.usage["format"]["detected_format"])
            if fa != fb and not any(e["source"] == f"artifact_{ia}" and e["target"] == f"artifact_{ib}" for e in edges):
                edges.append({"source": f"artifact_{ia}", "target": f"artifact_{ib}", "type": "transformed" if {fa, fb} == {"xlsx", "pptx"} else "related"})
    return ToolResult(
        job_id=job_id(), status="succeeded", tool=GRAPH_TOOL,
        validation=ValidationReport(status="passed", checks=[
            ValidationCheck(name="artifacts_inspected", status="passed", details={"artifact_count": len(artifact_paths), "inspected_count": len(nodes)}),
            ValidationCheck(name="graph_built", status="passed", details={"node_count": len(nodes), "edge_count": len(edges)}),
        ]),
        usage={"summary": {"artifact_count": len(nodes), "edge_count": len(edges)}, "graph": {"nodes": nodes, "edges": edges}},
        next_recommended_tools=["office.bundle.export", "office.bundle.verify"])


# -- internal helpers --

def _apply_format_patch(fmt: str, inp: Path, out: Path, ops: list[dict[str, Any]]) -> ToolResult:
    if fmt == "docx":
        conv = [{"op": "replace_paragraph", "paragraph_index": int(o.get("paragraph_index", 0)), "text": str(o.get("replace") or o.get("text") or "")} if o.get("op") == "replace_text" else {"op": "append_paragraph", "text": str(o.get("text") or "style update")} for o in ops]
        return apply_word_patch(input_path=inp, output_path=out, operations=conv)
    if fmt == "xlsx":
        xlsx_ops = [(kind, fn, [o for o in ops if o.get("op") == kind])
                     for kind, fn in [("set_value", patch_sheet_cells), ("replace_formula", patch_sheet_formulas), ("update_range", patch_sheet_table)]]
        applicable = [(fn, matched) for _, fn, matched in xlsx_ops if matched]
        if not applicable:
            return failed_result(REVIEW_PATCH_TOOL, OKofficeError(code="invalid_input", message="No applicable xlsx patch operations."))
        current_input = inp
        for fn, matched in applicable:
            result = fn(path=current_input, output_path=out, operations=matched)
            if result.status == "failed":
                return result
            current_input = out
        return result
    if fmt == "pptx":
        return apply_deck_patch(input_path=inp, output_path=out, operations=ops)
    return failed_result(REVIEW_PATCH_TOOL, OKofficeError(code="unsupported_file_type", message=f"No patch delegate for format: {fmt}"))


def _extract_text(path: Path, fmt: str) -> str:
    try:
        with zipfile.ZipFile(path) as zf:
            if fmt == "docx":
                root = ET.fromstring(zf.read("word/document.xml"))
                return " ".join(n.text for n in root.iter(f"{{{_XML_NS['docx']}}}t") if n.text)
            if fmt == "xlsx":
                names = {n.replace("\\", "/") for n in zf.namelist()}
                if "xl/sharedStrings.xml" not in names:
                    return ""
                root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
                return " ".join(n.text for n in root.iter(f"{{{_XML_NS['xlsx']}}}t") if n.text)
            if fmt == "pptx":
                parts: list[str] = []
                for name in sorted(zf.namelist()):
                    if name.startswith("ppt/slides/slide") and name.endswith(".xml"):
                        root = ET.fromstring(zf.read(name))
                        parts.extend(n.text for n in root.iter(f"{{{_XML_NS['pptx']}}}t") if n.text)
                return " ".join(parts)
    except Exception:
        pass
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _find_locations(text: str, term: str) -> list[dict[str, Any]]:
    locs: list[dict[str, Any]] = []
    low_text, low_term, start = text.lower(), term.lower(), 0
    while len(locs) < 50:
        pos = low_text.find(low_term, start)
        if pos == -1:
            break
        cs, ce = max(0, pos - 20), min(len(text), pos + len(term) + 20)
        locs.append({"offset": pos, "context": text[cs:ce]})
        start = pos + 1
    return locs


def _step(r: ToolResult) -> dict[str, Any]:
    return {"tool": r.tool, "status": r.status, "job_id": r.job_id}


def _dedupe(warnings: list[str]) -> list[str]:
    seen: set[str] = set()
    return [w for w in warnings if w and w not in seen and not seen.add(w)]
