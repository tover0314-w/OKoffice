from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentpdf.artifacts.store import build_artifact
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import AgentPDFError, ToolResult, ValidationCheck, ValidationReport


def extract_schema(
    context_packet_or_path: dict[str, Any] | str | Path,
    schema: dict[str, Any],
    output_path: str | Path | None = None,
) -> ToolResult:
    tool = "office.extract.schema"
    try:
        packet = _load_context_packet_value(context_packet_or_path)
        fields = _simple_schema_fields(schema)
        records = _extract_evidence_records(packet, fields)
        matched_fields = {record["field"] for record in records}
        missing_fields = [field["name"] for field in fields if field["name"] not in matched_fields]
        evidence = {
            "context_packet_id": packet.get("context_packet_id"),
            "source_graph_id": _source_graph_id(packet),
            "fields": fields,
            "records": records,
            "missing_fields": missing_fields,
            "coverage": _coverage(len(records), len(fields)),
        }

        artifacts = []
        if output_path is not None:
            out_path = Path(output_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
            artifacts.append(build_artifact(out_path, source_tool=tool))

        warnings = [f"Missing evidence for fields: {', '.join(missing_fields)}."] if missing_fields else []
        return ToolResult(
            job_id=f"job_{uuid4().hex[:16]}",
            status="succeeded",
            tool=tool,
            artifacts=artifacts,
            validation=_schema_extraction_validation(fields, records, warnings),
            warnings=warnings,
            usage={"evidence": evidence},
            next_recommended_tools=["office.sheet.create_model", "office.workflow.extract_to_sheet"],
        )
    except AgentPDFException as exc:
        return _failed(tool, exc.to_error())


def extract_schema_from_context(
    *,
    context_packet_path: str | Path | None = None,
    context_packet: dict[str, Any] | None = None,
    schema: dict[str, Any] | str | Path | None = None,
    output_path: str | Path | None = None,
) -> ToolResult:
    tool = "office.extract.schema"
    try:
        packet = _load_context_packet(context_packet_path=context_packet_path, context_packet=context_packet)
        schema_obj = _load_schema(schema)
        fields = _schema_fields(schema_obj)
        nodes = _extractable_nodes(packet)
        row, source_refs = _extract_row(fields, nodes)
        missing_fields = [field["name"] for field in fields if row["values"].get(field["name"]) in {None, ""}]
        extraction = {
            "extraction_id": f"extract_{uuid4().hex[:16]}",
            "schema_name": str(schema_obj.get("name") or "schema"),
            "context_packet_id": packet.get("context_packet_id"),
            "fields": fields,
            "rows": [row],
            "source_refs": source_refs,
            "method": "local_label_value_match_v0",
        }
        artifacts = []
        if output_path is not None:
            out_path = Path(output_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(extraction, indent=2), encoding="utf-8")
            artifacts.append(build_artifact(out_path, source_tool=tool))

        warnings = [f"Missing extracted values for fields: {', '.join(missing_fields)}."] if missing_fields else []
        filled_value_count = len([value for value in row["values"].values() if value not in {None, ""}])
        return ToolResult(
            job_id=f"job_{uuid4().hex[:16]}",
            status="succeeded",
            tool=tool,
            artifacts=artifacts,
            validation=_validation_report(fields, nodes, extraction, warnings),
            warnings=warnings,
            usage={
                "summary": {
                    "field_count": len(fields),
                    "row_count": len(extraction["rows"]),
                    "source_count": len({ref["source_ref"] for ref in source_refs}),
                    "filled_value_count": filled_value_count,
                },
                "extraction": extraction,
                "source_refs": source_refs,
            },
            next_recommended_tools=["sheet.write.workbook", "office.workflow.extract_to_sheet"],
        )
    except AgentPDFException as exc:
        return _failed(tool, exc.to_error())


def _load_context_packet(
    *,
    context_packet_path: str | Path | None,
    context_packet: dict[str, Any] | None,
) -> dict[str, Any]:
    if context_packet is not None:
        return context_packet
    if context_packet_path is None:
        raise AgentPDFException("invalid_input", "context_packet_path or context_packet is required.")
    path = Path(context_packet_path)
    if not path.exists():
        raise AgentPDFException("file_not_found", f"Context packet not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AgentPDFException("invalid_input", "Context packet JSON must be an object.")
    return data


def _load_context_packet_value(context_packet_or_path: dict[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(context_packet_or_path, dict):
        return context_packet_or_path
    path = Path(context_packet_or_path)
    if not path.exists():
        raise AgentPDFException("file_not_found", f"Context packet not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AgentPDFException("invalid_input", "Context packet JSON must be an object.")
    return data


def _load_schema(schema: dict[str, Any] | str | Path | None) -> dict[str, Any]:
    if schema is None:
        raise AgentPDFException("invalid_input", "schema or schema_path is required.")
    if isinstance(schema, dict):
        return schema
    if isinstance(schema, Path) or (isinstance(schema, str) and Path(schema).exists()):
        data = json.loads(Path(schema).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise AgentPDFException("invalid_input", "Schema JSON must be an object.")
        return data
    if isinstance(schema, str):
        data = json.loads(schema)
        if not isinstance(data, dict):
            raise AgentPDFException("invalid_input", "Schema JSON must be an object.")
        return data
    raise AgentPDFException("invalid_input", "schema must be a JSON object, JSON string, or path.")


def _schema_fields(schema: dict[str, Any]) -> list[dict[str, Any]]:
    raw_fields = schema.get("fields")
    if not isinstance(raw_fields, list) or not raw_fields:
        raise AgentPDFException("invalid_input", "schema.fields must include at least one field.")
    fields = []
    for raw_field in raw_fields:
        if not isinstance(raw_field, dict) or not raw_field.get("name"):
            raise AgentPDFException("invalid_input", "Every schema field must be an object with a name.")
        name = str(raw_field["name"])
        raw_aliases = raw_field.get("aliases")
        aliases = [str(alias) for alias in raw_aliases] if isinstance(raw_aliases, list) else []
        if name not in aliases:
            aliases.append(name)
        title_alias = name.replace("_", " ").title()
        if title_alias not in aliases:
            aliases.append(title_alias)
        fields.append(
            {
                "name": name,
                "type": str(raw_field.get("type") or "string"),
                "aliases": aliases,
                "required": bool(raw_field.get("required", False)),
            }
        )
    return fields


def _simple_schema_fields(schema: dict[str, Any]) -> list[dict[str, Any]]:
    raw_fields = schema.get("fields")
    if not isinstance(raw_fields, list) or not raw_fields:
        raise AgentPDFException("invalid_input", "schema.fields must include at least one field.")
    fields: list[dict[str, Any]] = []
    for raw_field in raw_fields:
        if not isinstance(raw_field, dict) or not raw_field.get("name"):
            raise AgentPDFException("invalid_input", "Every schema field must be an object with a name.")
        fields.append({"name": str(raw_field["name"]), "type": str(raw_field.get("type") or "string")})
    return fields


def _source_graph_id(packet: dict[str, Any]) -> str | None:
    source_graph = packet.get("source_graph")
    if not isinstance(source_graph, dict):
        return None
    source_graph_id = source_graph.get("source_graph_id")
    return str(source_graph_id) if source_graph_id is not None else None


def _extract_evidence_records(packet: dict[str, Any], fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = _evidence_candidates(packet)
    records: list[dict[str, Any]] = []
    for field in fields:
        match = _find_evidence_match(field["name"], candidates)
        if match is None:
            continue
        records.append(
            {
                "field": field["name"],
                "type": field["type"],
                "value": _normalize_value(match["value"], field["type"]),
                "source_ref": match.get("source_ref"),
                "source_id": match.get("source_id"),
                "locator": match.get("locator"),
                "matched_text": match["matched_text"],
                "match_source": match["match_source"],
                "confidence": 0.9,
            }
        )
    return records


def _evidence_candidates(packet: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    source_graph = packet.get("source_graph")
    nodes = source_graph.get("nodes") if isinstance(source_graph, dict) else []
    if isinstance(nodes, list):
        for index, node in enumerate(nodes):
            if not isinstance(node, dict):
                continue
            for key in ("text", "evidence_text", "label", "file_name"):
                value = str(node.get(key) or "").strip()
                if not value:
                    continue
                candidates.append(
                    {
                        "text": value,
                        "source_ref": node.get("source_ref"),
                        "source_id": node.get("source_id"),
                        "locator": node.get("locator"),
                        "match_source": f"source_graph.nodes[{index}].{key}",
                    }
                )

    items = packet.get("items")
    if isinstance(items, list):
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            for key in ("label", "file_name"):
                value = str(item.get(key) or "").strip()
                if not value:
                    continue
                candidates.append(
                    {
                        "text": value,
                        "source_ref": item.get("source_ref"),
                        "source_id": item.get("context_item_id"),
                        "locator": None,
                        "match_source": f"items[{index}].{key}",
                    }
                )
    return candidates


def _find_evidence_match(field_name: str, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    for candidate in candidates:
        for line in str(candidate["text"]).splitlines():
            match = _match_field_line(field_name, line, require_label_value=True)
            if match is None:
                continue
            return {**candidate, **match}
    for candidate in candidates:
        for line in str(candidate["text"]).splitlines():
            match = _match_field_line(field_name, line)
            if match is None:
                continue
            return {**candidate, **match}
    return None


def _match_field_line(field_name: str, line: str, *, require_label_value: bool = False) -> dict[str, str] | None:
    stripped = line.strip()
    if not stripped:
        return None
    if ":" in stripped:
        label, value = stripped.split(":", 1)
        if _tokens_match(field_name, label):
            return {"value": value.strip(), "matched_text": stripped}
        return None
    if require_label_value:
        return None
    if _tokens_match(field_name, stripped):
        return {"value": stripped, "matched_text": stripped}
    return None


def _tokens_match(field_name: str, text: str) -> bool:
    field_tokens = _tokens(field_name)
    text_tokens = set(_tokens(text))
    return bool(field_tokens) and all(token in text_tokens for token in field_tokens)


def _tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.lower().replace("_", " "))


def _coverage(matched: int, total: int) -> dict[str, float | int]:
    ratio = round(matched / total, 4) if total else 0.0
    return {"matched": matched, "total": total, "ratio": ratio}


def _schema_extraction_validation(
    fields: list[dict[str, Any]],
    records: list[dict[str, Any]],
    warnings: list[str],
) -> ValidationReport:
    return ValidationReport(
        status="warning" if warnings else "passed",
        checks=[
            ValidationCheck(name="schema_fields_declared", status="passed", details={"field_count": len(fields)}),
            ValidationCheck(name="evidence_records_emitted", status="passed", details={"record_count": len(records)}),
        ],
        warnings=warnings,
    )


def _extractable_nodes(packet: dict[str, Any]) -> list[dict[str, Any]]:
    graph = packet.get("source_graph")
    nodes = graph.get("nodes") if isinstance(graph, dict) else None
    if not isinstance(nodes, list):
        raise AgentPDFException("invalid_input", "Context packet must include source_graph.nodes.")
    return [node for node in nodes if isinstance(node, dict) and str(node.get("text") or "").strip()]


def _extract_row(fields: list[dict[str, Any]], nodes: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    values: dict[str, str | None] = {}
    field_evidence: dict[str, dict[str, Any]] = {}
    source_refs: list[dict[str, Any]] = []
    for field in fields:
        match = _find_field_match(field, nodes)
        values[field["name"]] = match["value"] if match else None
        if match is None:
            continue
        evidence = {
            "source_ref": match["node"].get("source_ref"),
            "source_id": match["node"].get("source_id"),
            "source_type": match["node"].get("source_type"),
            "locator": match["node"].get("locator"),
            "matched_alias": match["alias"],
            "excerpt": match["excerpt"],
            "confidence": 0.95,
        }
        field_evidence[field["name"]] = evidence
        source_ref_entry = {
            "source_ref": evidence["source_ref"],
            "source_id": evidence["source_id"],
            "source_type": evidence["source_type"],
            "locator": evidence["locator"],
        }
        if source_ref_entry not in source_refs:
            source_refs.append(source_ref_entry)
    return {"row_id": "row_001", "values": values, "field_evidence": field_evidence}, source_refs


def _find_field_match(field: dict[str, Any], nodes: list[dict[str, Any]]) -> dict[str, Any] | None:
    for node in nodes:
        text = str(node.get("text") or "")
        for alias in field["aliases"]:
            value, excerpt = _extract_label_value(text, alias)
            if value is None:
                continue
            return {
                "node": node,
                "alias": alias,
                "value": _normalize_value(value, str(field["type"])),
                "excerpt": excerpt,
            }
    return None


def _extract_label_value(text: str, alias: str) -> tuple[str | None, str | None]:
    pattern = re.compile(rf"^\s*{re.escape(alias)}\s*:\s*(?P<value>.+?)\s*$", re.IGNORECASE)
    for line in text.splitlines():
        match = pattern.match(line)
        if match:
            value = match.group("value").strip()
            return value, line.strip()
    return None, None


def _normalize_value(value: str, field_type: str) -> str:
    if field_type == "number":
        normalized = value.strip().replace("$", "").replace(",", "")
        return normalized
    return value.strip()


def _validation_report(
    fields: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
    extraction: dict[str, Any],
    warnings: list[str],
) -> ValidationReport:
    return ValidationReport(
        status="warning" if warnings else "passed",
        checks=[
            ValidationCheck(name="schema_fields_declared", status="passed", details={"field_count": len(fields)}),
            ValidationCheck(name="source_nodes_available", status="passed", details={"source_node_count": len(nodes)}),
            ValidationCheck(
                name="rows_extracted",
                status="passed",
                details={"row_count": len(extraction["rows"])},
            ),
        ],
        warnings=warnings,
    )


def _failed(tool: str, error: AgentPDFError) -> ToolResult:
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="failed",
        tool=tool,
        error=error,
        warnings=[error.message],
    )
