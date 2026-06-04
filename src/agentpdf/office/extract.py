from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentpdf.artifacts.store import build_artifact
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import AgentPDFError, ToolResult, ValidationCheck, ValidationReport
from agentpdf.security.paths import resolve_input_path, resolve_output_path


TOOL_NAME = "office.extract.schema"


def extract_schema(
    context_packet_or_path: dict[str, Any] | str | Path,
    schema: dict[str, Any],
    output_path: str | Path | None = None,
) -> ToolResult:
    try:
        packet = _load_context_packet(context_packet_or_path)
        fields = _schema_fields(schema)
        candidates = _evidence_candidates(packet)
        records = _extract_records(fields, candidates)
        matched_fields = {record["field"] for record in records}
        missing_fields = [field["name"] for field in fields if field["name"] not in matched_fields]
        evidence = {
            "evidence_version": "0.1",
            "context_packet_id": packet.get("context_packet_id"),
            "source_graph_id": _source_graph_id(packet),
            "fields": fields,
            "records": records,
            "missing_fields": missing_fields,
            "coverage": _coverage(len(records), len(fields)),
            "method": "local_label_value_match_v0",
        }
        artifacts = []
        if output_path is not None:
            output = resolve_output_path(output_path)
            output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
            artifacts.append(build_artifact(output, TOOL_NAME))
        warnings = [f"Missing evidence for fields: {', '.join(missing_fields)}."] if missing_fields else []
        return ToolResult(
            job_id=_job_id(),
            status="succeeded",
            tool=TOOL_NAME,
            artifacts=artifacts,
            validation=_validation_report(fields, candidates, records, warnings),
            warnings=warnings,
            usage={
                "summary": {
                    "field_count": len(fields),
                    "record_count": len(records),
                    "missing_field_count": len(missing_fields),
                    "coverage": evidence["coverage"],
                    "context_packet_id": evidence["context_packet_id"],
                    "source_graph_id": evidence["source_graph_id"],
                },
                "evidence": evidence,
            },
            next_recommended_tools=["sheet.write.workbook", "office.workflow.extract_to_sheet"],
        )
    except AgentPDFException as exc:
        return _failed(exc.to_error())


def _load_context_packet(context_packet_or_path: dict[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(context_packet_or_path, dict):
        packet = context_packet_or_path
    else:
        path = resolve_input_path(context_packet_or_path)
        try:
            packet = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise AgentPDFException("invalid_context_packet", f"Context packet JSON is invalid: {path}") from exc
    if not isinstance(packet, dict) or not packet.get("context_packet_id"):
        raise AgentPDFException("invalid_context_packet", "Context packet must include context_packet_id.")
    if not isinstance(packet.get("items"), list):
        raise AgentPDFException("invalid_context_packet", "Context packet must include an items array.")
    if not isinstance(packet.get("source_graph"), dict):
        raise AgentPDFException("invalid_context_packet", "Context packet must include a source_graph object.")
    return packet


def _schema_fields(schema: dict[str, Any]) -> list[dict[str, Any]]:
    raw_fields = schema.get("fields")
    if not isinstance(raw_fields, list) or not raw_fields:
        raise AgentPDFException("invalid_input", "schema.fields must include at least one field.")
    fields: list[dict[str, Any]] = []
    for raw_field in raw_fields:
        if not isinstance(raw_field, dict) or not raw_field.get("name"):
            raise AgentPDFException("invalid_input", "Every schema field must be an object with a name.")
        fields.append(
            {
                "name": str(raw_field["name"]),
                "type": str(raw_field.get("type") or "string"),
                "required": bool(raw_field.get("required", False)),
                "aliases": _aliases(raw_field),
            }
        )
    return fields


def _aliases(raw_field: dict[str, Any]) -> list[str]:
    aliases = [str(alias) for alias in raw_field.get("aliases", []) if str(alias).strip()] if isinstance(raw_field.get("aliases"), list) else []
    name = str(raw_field["name"])
    for alias in (name, name.replace("_", " "), name.replace("_", " ").title()):
        if alias not in aliases:
            aliases.append(alias)
    return aliases


def _source_graph_id(packet: dict[str, Any]) -> str | None:
    graph = packet.get("source_graph")
    if not isinstance(graph, dict):
        return None
    value = graph.get("source_graph_id")
    return str(value) if value is not None else None


def _evidence_candidates(packet: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    graph = packet.get("source_graph", {}) if isinstance(packet.get("source_graph"), dict) else {}
    nodes = graph.get("nodes") if isinstance(graph.get("nodes"), list) else []
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        for key, text in _node_texts(node):
            if not text:
                continue
            candidates.append(
                {
                    "text": text,
                    "priority": _text_priority(key),
                    "source_ref": node.get("source_ref"),
                    "source_id": node.get("source_id") or node.get("node_id"),
                    "source_type": node.get("source_type") or node.get("type"),
                    "locator": _node_locator(node),
                    "match_source": f"source_graph.nodes[{index}].{key}",
                }
            )
    for index, item in enumerate(packet.get("items", [])):
        if not isinstance(item, dict):
            continue
        for key, text in _item_texts(item):
            if not text:
                continue
            candidates.append(
                {
                    "text": text,
                    "priority": _text_priority(key) + 5,
                    "source_ref": item.get("source_ref"),
                    "source_id": item.get("context_item_id"),
                    "source_type": item.get("type"),
                    "locator": None,
                    "match_source": f"items[{index}].{key}",
                }
            )
    return candidates


def _node_texts(node: dict[str, Any]) -> list[tuple[str, str]]:
    texts: list[tuple[str, str]] = []
    for key in ("text", "evidence_text", "label"):
        value = str(node.get(key) or "").strip()
        if value:
            texts.append((key, value))
    evidence = node.get("evidence")
    if isinstance(evidence, dict):
        for key in ("text", "summary", "excerpt"):
            value = str(evidence.get(key) or "").strip()
            if value:
                texts.append((f"evidence.{key}", value))
        compact = _evidence_label_lines(evidence)
        if compact:
            texts.append(("evidence", compact))
    return texts


def _text_priority(key: str) -> int:
    if key in {"text", "evidence_text"}:
        return 0
    if key == "content.text":
        return 1
    if key.startswith("evidence"):
        return 2
    return 3


def _item_texts(item: dict[str, Any]) -> list[tuple[str, str]]:
    texts: list[tuple[str, str]] = []
    for key in ("label", "file_name"):
        value = str(item.get(key) or "").strip()
        if value:
            texts.append((key, value))
    content = item.get("content")
    if isinstance(content, dict):
        value = str(content.get("text") or "").strip()
        if value:
            texts.append(("content.text", value))
    return texts


def _evidence_label_lines(evidence: dict[str, Any]) -> str:
    lines = []
    for key, value in evidence.items():
        if isinstance(value, (str, int, float)) and str(value).strip():
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


def _node_locator(node: dict[str, Any]) -> dict[str, Any] | None:
    locator = node.get("locator")
    if isinstance(locator, dict):
        return locator
    locators = node.get("locators")
    if isinstance(locators, list) and locators and isinstance(locators[0], dict):
        return locators[0]
    return None


def _extract_records(fields: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records = []
    for field in fields:
        match = _find_match(field, candidates)
        if match is None:
            continue
        records.append(
            {
                "field": field["name"],
                "type": field["type"],
                "value": _normalize_value(str(match["value"]), field["type"]),
                "source_ref": match.get("source_ref"),
                "source_id": match.get("source_id"),
                "source_type": match.get("source_type"),
                "locator": match.get("locator"),
                "matched_text": match["matched_text"],
                "match_source": match["match_source"],
                "confidence": 0.9,
            }
        )
    return records


def _find_match(field: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    sorted_candidates = sorted(candidates, key=lambda candidate: int(candidate.get("priority", 0)))
    for require_label in (True, False):
        for candidate in sorted_candidates:
            for line in str(candidate["text"]).splitlines():
                for alias in field["aliases"]:
                    match = _match_line(alias, line, require_label_value=require_label)
                    if match is not None:
                        return {**candidate, **match}
    return None


def _match_line(alias: str, line: str, *, require_label_value: bool) -> dict[str, str] | None:
    stripped = line.strip()
    if not stripped:
        return None
    if ":" in stripped:
        label, value = stripped.split(":", 1)
        if _tokens_match(alias, label):
            return {"value": value.strip(), "matched_text": stripped}
        return None
    if require_label_value:
        return None
    if _tokens_match(alias, stripped):
        return {"value": stripped, "matched_text": stripped}
    return None


def _tokens_match(alias: str, text: str) -> bool:
    alias_tokens = _tokens(alias)
    text_tokens = set(_tokens(text))
    return bool(alias_tokens) and all(token in text_tokens for token in alias_tokens)


def _tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.lower().replace("_", " "))


def _normalize_value(value: str, field_type: str) -> str:
    if field_type == "number":
        return value.strip().replace("$", "").replace(",", "")
    return value.strip()


def _coverage(matched: int, total: int) -> dict[str, float | int]:
    return {"matched": matched, "total": total, "ratio": round(matched / total, 4) if total else 0.0}


def _validation_report(
    fields: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    records: list[dict[str, Any]],
    warnings: list[str],
) -> ValidationReport:
    return ValidationReport(
        status="warning" if warnings else "passed",
        checks=[
            ValidationCheck(name="schema_fields_declared", status="passed", details={"field_count": len(fields)}),
            ValidationCheck(name="candidate_text_scanned", status="passed", details={"candidate_count": len(candidates)}),
            ValidationCheck(name="evidence_records_emitted", status="passed", details={"record_count": len(records)}),
        ],
        warnings=warnings,
    )


def _failed(error: AgentPDFError) -> ToolResult:
    return ToolResult(job_id=_job_id(), status="failed", tool=TOOL_NAME, error=error, warnings=[error.message])


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
