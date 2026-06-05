from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any
from uuid import uuid4
from xml.etree import ElementTree

from okoffice.artifacts.store import build_artifact
from okoffice.office.word import WORD_DOCUMENT, W_NS, inspect_word_document
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport
from okoffice.security.paths import resolve_input_path, resolve_output_path


PLAN_TOOL = "word.patch.plan"
APPLY_TOOL = "word.patch.apply"
W_URI = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
ElementTree.register_namespace("w", W_URI)


def plan_word_patch(*, input_path: str | Path, operations: list[dict[str, Any]]) -> ToolResult:
    try:
        input_file = resolve_input_path(input_path)
        document, paragraphs = _load_document(input_file)
        normalized = _normalize_operations(operations)
        preview = _preview_changes(paragraphs, normalized)
        return ToolResult(
            job_id=_job_id(),
            status="succeeded",
            tool=PLAN_TOOL,
            validation=_plan_validation(input_file, normalized, preview),
            usage={
                "summary": {
                    "operation_count": len(normalized),
                    "input_paragraph_count": len(paragraphs),
                    "change_count": len(preview["changes"]),
                },
                "preview": preview,
                "patch_transaction": _transaction(input_file=input_file, output_file=None, operations=normalized),
            },
            next_recommended_tools=["word.patch.apply", "word.inspect.document"],
        )
    except OKofficeException as exc:
        return _failed(PLAN_TOOL, exc.to_error())
    except (zipfile.BadZipFile, ElementTree.ParseError, ValueError) as exc:
        return _failed(PLAN_TOOL, OKofficeError(code="invalid_input", message=str(exc)))


def apply_word_patch(
    *,
    input_path: str | Path,
    output_path: str | Path,
    operations: list[dict[str, Any]],
) -> ToolResult:
    try:
        input_file = resolve_input_path(input_path)
        output_file = resolve_output_path(output_path)
        if input_file == output_file:
            raise OKofficeException(
                "invalid_input",
                "word.patch.apply writes to a new output_path and never mutates the input document.",
                details={"input_path": input_file.as_posix(), "output_path": output_file.as_posix()},
            )
        if output_file.suffix.lower() != ".docx":
            raise OKofficeException(
                "unsupported_file_type",
                "word.patch.apply writes .docx output files.",
                details={"output_path": output_file.as_posix()},
            )

        document, paragraphs = _load_document(input_file)
        normalized = _normalize_operations(operations)
        preview = _preview_changes(paragraphs, normalized)
        _apply_operations(document, paragraphs, normalized)
        output_xml = ElementTree.tostring(document, encoding="utf-8", xml_declaration=True)
        _write_patched_package(input_file, output_file, output_xml)

        inspected = inspect_word_document(output_file)
        if inspected.status != "succeeded":
            raise OKofficeException(
                "output_validation_failed",
                "Patched Word document could not be inspected.",
                details=inspected.error.model_dump(mode="json") if inspected.error else {},
            )

        return ToolResult(
            job_id=_job_id(),
            status="succeeded",
            tool=APPLY_TOOL,
            artifacts=[build_artifact(output_file, source_tool=APPLY_TOOL)],
            validation=_apply_validation(input_file, output_file, inspected, normalized),
            usage={
                "summary": {
                    "operation_count": len(normalized),
                    "input_paragraph_count": len(paragraphs),
                    "output_paragraph_count": inspected.usage.get("summary", {}).get("paragraph_count", 0),
                    "change_count": len(preview["changes"]),
                },
                "preview": preview,
                "patch_transaction": _transaction(input_file=input_file, output_file=output_file, operations=normalized),
            },
            next_recommended_tools=["word.inspect.document", "office.context.build_packet"],
        )
    except OKofficeException as exc:
        return _failed(APPLY_TOOL, exc.to_error())
    except (zipfile.BadZipFile, ElementTree.ParseError, ValueError) as exc:
        return _failed(APPLY_TOOL, OKofficeError(code="invalid_input", message=str(exc)))


def _load_document(path: Path) -> tuple[ElementTree.Element, list[ElementTree.Element]]:
    if path.suffix.lower() not in {".docx", ".docm"} or not zipfile.is_zipfile(path):
        raise OKofficeException(
            "unsupported_file_type",
            f"Word patch requires a readable DOCX/DOCM package: {path.name}",
            details={"path": path.as_posix()},
        )
    with zipfile.ZipFile(path) as archive:
        names = {name.replace("\\", "/") for name in archive.namelist()}
        unsafe_entries = [name for name in names if _unsafe_zip_entry(name)]
        if unsafe_entries:
            raise OKofficeException(
                "unsafe_input_rejected",
                "Word package contains unsafe ZIP entry names.",
                details={"unsafe_package_entries": unsafe_entries},
            )
        if WORD_DOCUMENT not in names:
            raise OKofficeException(
                "unsupported_file_type",
                "Word package is missing word/document.xml.",
                details={"path": path.as_posix()},
            )
        document = ElementTree.fromstring(archive.read(WORD_DOCUMENT))
    body = document.find(f"{W_NS}body")
    paragraphs = [] if body is None else [child for child in list(body) if child.tag == f"{W_NS}p"]
    return document, paragraphs


def _normalize_operations(operations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(operations, list) or not operations:
        raise OKofficeException("invalid_input", "Word patch operations must be a non-empty list.")
    normalized = []
    for index, operation in enumerate(operations, start=1):
        if not isinstance(operation, dict):
            raise OKofficeException("invalid_input", f"Word patch operation {index} must be an object.")
        op = str(operation.get("op") or "")
        if op not in {"replace_paragraph", "append_paragraph", "insert_paragraph_after"}:
            raise OKofficeException("invalid_input", f"Unsupported Word patch operation: {op or '<missing>'}")
        text = str(operation.get("text") or "")
        if not text:
            raise OKofficeException("invalid_input", f"Word patch operation {index} requires non-empty text.")
        normalized_operation = {"op": op, "text": text}
        if op in {"replace_paragraph", "insert_paragraph_after"}:
            paragraph_index = operation.get("paragraph_index")
            if not isinstance(paragraph_index, int) or paragraph_index < 0:
                raise OKofficeException(
                    "invalid_input",
                    f"Word patch operation {index} requires a zero-based paragraph_index.",
                )
            normalized_operation["paragraph_index"] = paragraph_index
        normalized.append(normalized_operation)
    return normalized


def _preview_changes(
    paragraphs: list[ElementTree.Element],
    operations: list[dict[str, Any]],
) -> dict[str, Any]:
    changes = []
    for index, operation in enumerate(operations, start=1):
        op = operation["op"]
        paragraph_index = operation.get("paragraph_index")
        previous_text = None
        if isinstance(paragraph_index, int):
            if paragraph_index >= len(paragraphs):
                raise OKofficeException(
                    "invalid_input",
                    f"paragraph_index is outside the document paragraph range: {paragraph_index}",
                    details={"paragraph_count": len(paragraphs)},
                )
            previous_text = _text_content(paragraphs[paragraph_index])
        changes.append(
            {
                "operation_index": index,
                "op": op,
                "paragraph_index": paragraph_index,
                "previous_text": previous_text,
                "new_text": operation["text"],
            }
        )
    return {"changes": changes}


def _apply_operations(
    document: ElementTree.Element,
    paragraphs: list[ElementTree.Element],
    operations: list[dict[str, Any]],
) -> None:
    body = document.find(f"{W_NS}body")
    if body is None:
        raise OKofficeException("invalid_input", "Word document has no body.")
    for operation in operations:
        if operation["op"] == "replace_paragraph":
            _set_paragraph_text(paragraphs[int(operation["paragraph_index"])], str(operation["text"]))
        elif operation["op"] == "insert_paragraph_after":
            target_index = int(operation["paragraph_index"])
            new_paragraph = _paragraph(str(operation["text"]))
            body_children = list(body)
            insert_after = paragraphs[target_index]
            body.insert(body_children.index(insert_after) + 1, new_paragraph)
            paragraphs.insert(target_index + 1, new_paragraph)
        elif operation["op"] == "append_paragraph":
            new_paragraph = _paragraph(str(operation["text"]))
            section = body.find(f"{W_NS}sectPr")
            if section is None:
                body.append(new_paragraph)
            else:
                body.insert(list(body).index(section), new_paragraph)
            paragraphs.append(new_paragraph)


def _set_paragraph_text(paragraph: ElementTree.Element, text: str) -> None:
    preserved = [child for child in list(paragraph) if child.tag == f"{W_NS}pPr"]
    paragraph.clear()
    for child in preserved:
        paragraph.append(child)
    paragraph.append(_run(text))


def _paragraph(text: str) -> ElementTree.Element:
    paragraph = ElementTree.Element(f"{W_NS}p")
    paragraph.append(_run(text))
    return paragraph


def _run(text: str) -> ElementTree.Element:
    run = ElementTree.Element(f"{W_NS}r")
    node = ElementTree.SubElement(run, f"{W_NS}t")
    node.text = text
    return run


def _write_patched_package(input_file: Path, output_file: Path, document_xml: bytes) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(input_file) as source, zipfile.ZipFile(output_file, "w", zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            name = info.filename.replace("\\", "/")
            if _unsafe_zip_entry(name):
                raise OKofficeException(
                    "unsafe_input_rejected",
                    "Word package contains unsafe ZIP entry names.",
                    details={"unsafe_package_entries": [name]},
                )
            if name == WORD_DOCUMENT:
                target.writestr(name, document_xml)
            else:
                target.writestr(name, source.read(info.filename))


def _transaction(
    *,
    input_file: Path,
    output_file: Path | None,
    operations: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "transaction_id": f"patch_{uuid4().hex[:16]}",
        "input_path": input_file.as_posix(),
        "output_path": output_file.as_posix() if output_file else None,
        "mutates_inputs": False,
        "operation_count": len(operations),
        "operations": operations,
        "rollback": {
            "strategy": "discard_output",
            "input_preserved": True,
        },
    }


def _plan_validation(path: Path, operations: list[dict[str, Any]], preview: dict[str, Any]) -> ValidationReport:
    return ValidationReport(
        status="passed",
        checks=[
            ValidationCheck(name="input_path_safe", status="passed", details={"path": path.as_posix()}),
            ValidationCheck(name="operations_validated", status="passed", details={"operation_count": len(operations)}),
            ValidationCheck(name="preview_built", status="passed", details={"change_count": len(preview["changes"])}),
        ],
    )


def _apply_validation(
    input_file: Path,
    output_file: Path,
    inspected: ToolResult,
    operations: list[dict[str, Any]],
) -> ValidationReport:
    return ValidationReport(
        status="passed",
        checks=[
            ValidationCheck(name="input_path_safe", status="passed", details={"path": input_file.as_posix()}),
            ValidationCheck(name="output_path_distinct", status="passed", details={"path": output_file.as_posix()}),
            ValidationCheck(name="operations_applied", status="passed", details={"operation_count": len(operations)}),
            ValidationCheck(
                name="word_patch_reopened_by_inspect",
                status="passed",
                details=inspected.usage.get("summary", {}),
            ),
        ],
    )


def _text_content(element: ElementTree.Element) -> str:
    values = []
    for node in element.iter():
        if node.tag in {f"{W_NS}t", f"{W_NS}instrText"} and node.text:
            values.append(node.text)
    return "".join(values).strip()


def _unsafe_zip_entry(name: str) -> bool:
    normalized = name.replace("\\", "/")
    return normalized.startswith("/") or normalized.startswith("../") or "/../" in normalized


def _failed(tool: str, error: OKofficeError) -> ToolResult:
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool=tool,
        error=error,
        warnings=[error.message],
    )


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
