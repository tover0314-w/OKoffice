"""Cross-format heuristic extraction: claims, entities, obligations."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from okoffice.office.deck_extract import extract_deck_text
from okoffice.office.inspect import inspect_office_file
from okoffice.office.shared import failed_result, job_id
from okoffice.office.sheet import read_sheet_workbook
from okoffice.office.word_extract import extract_word_text
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport
from okoffice.security.paths import resolve_input_path

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
MONTH_NAMES = r"January|February|March|April|May|June|July|August|September|October|November|December"

CLAIM_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("percentage", re.compile(r"\d+\.?\d*\s*%")),
    ("dollar_amount", re.compile(r"\$\s*[\d,.]+")),
    ("superlative", re.compile(r"\b(largest|smallest|best|worst|first|last|most|least|highest|lowest)\b", re.I)),
    ("comparative", re.compile(r"\b(more|less|higher|lower|greater|fewer)\s+than\b", re.I)),
    ("obligation", re.compile(r"\b(shall|must|is required to|will)\b", re.I)),
]
ENTITY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("capitalized_phrase", re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b")),
    ("date_mdy", re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")),
    ("date_named", re.compile(rf"\b(?:{MONTH_NAMES})\s+\d{{1,2}},?\s*\d{{4}}\b", re.I)),
    ("money", re.compile(r"\$\s*[\d,.]+(?:\s*(?:million|billion|trillion))?\b", re.I)),
]
OBLIGATION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("modal_obligation", re.compile(r"\b(shall|must|is required to|is required|are required to|are required)\b", re.I)),
    ("verb_obligation", re.compile(r"\b(will|shall)\s+(provide|submit|deliver|ensure|maintain|comply|implement|complete|perform)\b", re.I)),
]


def _text_from_office(path: str | Path) -> tuple[str, str, list[str]]:
    """Return (text, detected_format, warnings) from any Office file."""
    preflight = inspect_office_file(path)
    if preflight.status == "failed":
        raise ValueError((preflight.error or OKofficeError(code="unsupported_file_type", message="Preflight failed.")).message)
    detected = preflight.usage["format"]["detected_format"]
    resolved = Path(preflight.usage["file"]["path"])
    if detected == "docx":
        r = extract_word_text(resolved)
        return (str(r.usage.get("text", "")) if r.status == "succeeded" else ""), detected, list(preflight.warnings)
    if detected == "xlsx":
        r = read_sheet_workbook(resolved, max_rows_per_sheet=500)
        if r.status != "succeeded":
            return "", detected, list(preflight.warnings)
        parts = [str(c.get("value", "")).strip() for s in r.usage.get("sheets", []) for rw in s.get("rows", []) for c in rw.get("cells", []) if str(c.get("value", "")).strip()]
        return "\n".join(parts), detected, list(preflight.warnings)
    if detected == "pptx":
        r = extract_deck_text(resolved)
        text = "\n".join(sl.get("text", "") for sl in r.usage.get("slides", [])) if r.status == "succeeded" else ""
        return text, detected, list(preflight.warnings)
    raise ValueError(f"Unsupported format: {detected}")


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_RE.split(text) if s.strip()]


def _location(fmt: str, path: Path, idx: int) -> dict[str, Any]:
    return {"format": fmt, "path": str(path), "sentence_index": idx}


def _ok_result(tool: str, fmt: str, kind: str, items: list[dict[str, Any]], warnings: list[str], summary: dict[str, Any], next_tools: list[str]) -> ToolResult:
    return ToolResult(job_id=job_id(), status="succeeded", tool=tool,
        validation=ValidationReport(status="passed", checks=[
            ValidationCheck(name="format_supported", status="passed", details={"detected_format": fmt}),
            ValidationCheck(name=f"{kind}_extracted", status="passed", details={f"{kind}_count": len(items)}),
        ]), warnings=warnings, usage={"summary": summary, kind + "s": items}, next_recommended_tools=next_tools)


# -- 1. office.extract.claims ------------------------------------------------

def extract_office_claims(path: str | Path) -> ToolResult:
    """Extract claim-like sentences from any Office document."""
    try:
        resolved = resolve_input_path(path)
        text, detected, warnings = _text_from_office(resolved)
        claims, seen = [], set()
        for idx, sent in enumerate(_sentences(text)):
            for ctype, pat in CLAIM_PATTERNS:
                if pat.search(sent) and (idx, ctype) not in seen:
                    seen.add((idx, ctype))
                    claims.append({"text": sent, "claim_type": ctype, "source_location": _location(detected, resolved, idx)})
        tc: dict[str, int] = {}
        for c in claims:
            tc[c["claim_type"]] = tc.get(c["claim_type"], 0) + 1
        return _ok_result("office.extract.claims", detected, "claim", claims, warnings,
            {"claim_count": len(claims), "claim_types": tc},
            ["office.extract.entities", "office.extract.obligations"])
    except Exception as exc:
        return failed_result("office.extract.claims", OKofficeError(code="extraction_failed", message=str(exc)))


# -- 2. office.extract.entities ----------------------------------------------

def extract_office_entities(path: str | Path) -> ToolResult:
    """Extract named entities heuristically from any Office document."""
    try:
        resolved = resolve_input_path(path)
        text, detected, warnings = _text_from_office(resolved)
        entities, seen = [], set()
        for etype, pat in ENTITY_PATTERNS:
            for m in pat.finditer(text):
                key = (m.group(0).strip(), etype)
                if key not in seen:
                    seen.add(key)
                    entities.append({"text": key[0], "entity_type": etype,
                        "source_location": {"format": detected, "path": str(resolved), "start": m.start(), "end": m.end()}})
        tc: dict[str, int] = {}
        for e in entities:
            tc[e["entity_type"]] = tc.get(e["entity_type"], 0) + 1
        return _ok_result("office.extract.entities", detected, "entity", entities, warnings,
            {"entity_count": len(entities), "entity_types": tc},
            ["office.extract.claims", "office.extract.obligations"])
    except Exception as exc:
        return failed_result("office.extract.entities", OKofficeError(code="extraction_failed", message=str(exc)))


# -- 3. office.extract.obligations -------------------------------------------

def extract_office_obligations(path: str | Path) -> ToolResult:
    """Extract obligation sentences from any Office document."""
    try:
        resolved = resolve_input_path(path)
        text, detected, warnings = _text_from_office(resolved)
        obligations, seen = [], set()
        for idx, sent in enumerate(_sentences(text)):
            for otype, pat in OBLIGATION_PATTERNS:
                if pat.search(sent) and (idx, otype) not in seen:
                    seen.add((idx, otype))
                    obligations.append({"text": sent, "obligation_type": otype, "source_location": _location(detected, resolved, idx)})
        return _ok_result("office.extract.obligations", detected, "obligation", obligations, warnings,
            {"obligation_count": len(obligations)},
            ["office.extract.claims", "office.extract.entities"])
    except Exception as exc:
        return failed_result("office.extract.obligations", OKofficeError(code="extraction_failed", message=str(exc)))
