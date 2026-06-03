from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from pydantic import ValidationError

from agentpdf.artifacts.store import build_artifact
from agentpdf.authoring.models import PageDocument
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import ToolResult, ValidationCheck, ValidationReport
from agentpdf.security.paths import resolve_output_path


TOOL_NAME = "pdf.create.html_package"
COLOR_TOKEN_FIELDS = {"primary_color", "accent_color", "warning_color", "background_color", "dark_color"}
CSS_INJECTION_MARKERS = ("</style", "<script", "url(", "@import", "javascript:", "data:")
FONT_FORBIDDEN_MARKERS = ("<", ">", "{", "}", ";", "url(", "@", "javascript:", "data:")
HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def write_authoring_html_package(
    *,
    page_document: PageDocument | dict[str, Any],
    html_output_path: str | Path,
    title: str | None = None,
) -> ToolResult:
    try:
        document = (
            page_document
            if isinstance(page_document, PageDocument)
            else PageDocument.model_validate(page_document)
        )
        _reject_unsafe_design_tokens(document)
        _reject_unsafe_blocks(document)
        output = resolve_output_path(html_output_path)
        manifest_path = output.with_suffix(".html-manifest.json")
        validation = _validate(document)
        manifest = _manifest(document, output=output, manifest_path=manifest_path, validation=validation)
        output.write_text(_html_document(document, title=title or _document_title(document)), encoding="utf-8")
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return ToolResult(
            job_id=_job_id(),
            status="succeeded" if validation.status == "passed" else "failed",
            tool=TOOL_NAME,
            artifacts=[
                build_artifact(output, source_tool=TOOL_NAME),
                build_artifact(manifest_path, source_tool=TOOL_NAME),
            ],
            validation=validation,
            usage={
                "html_output_path": str(output.resolve()),
                "html_package_manifest_path": str(manifest_path.resolve()),
                "html_package_manifest": manifest,
                "page_document": document.model_dump(mode="json"),
            },
            next_recommended_tools=["pdf.render.html_package", "pdf.qa.visual_report"],
        )
    except AgentPDFException as exc:
        return ToolResult(
            job_id=_job_id(),
            status="failed",
            tool=TOOL_NAME,
            warnings=[exc.message],
            error=exc.to_error(),
        )
    except ValidationError as exc:
        return _failed_validation(
            "Page document payload is invalid or unsafe.",
            code=_validation_error_code(exc),
            payload="page_document",
            validation_error=exc,
        )


def _html_document(document: PageDocument, *, title: str) -> str:
    tokens = document.design_tokens
    pages = "\n".join(_page_html(page) for page in document.pages)
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '  <meta charset="utf-8" />',
            "  <meta http-equiv=\"Content-Security-Policy\" "
            "content=\"default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; "
            "font-src 'self' data:; script-src 'none';\" />",
            f"  <title>{html.escape(title)}</title>",
            '  <meta name="agentpdf:renderer" content="authoring-html-package-v0" />',
            "  <style>",
            _stylesheet(tokens.model_dump(mode="json")),
            "  </style>",
            "</head>",
            f'<body data-agentpdf-authoring-document data-page-document-id="{_attr(document.page_document_id)}">',
            pages,
            "</body>",
            "</html>",
        ]
    )


def _page_html(page: Any) -> str:
    blocks = "\n".join(_block_html(block) for block in page.blocks)
    footer = f"    <footer>{html.escape(page.source_footer)}</footer>" if page.source_footer else "    <footer></footer>"
    return "\n".join(
        [
            f'  <section class="slide slide-{_class_token(page.layout)}" data-page-number="{page.page_number}" data-layout="{_attr(page.layout)}">',
            f'    <p class="page-kicker">{html.escape(page.layout)}</p>',
            f"    <h1>{html.escape(page.title)}</h1>",
            f'    <p class="subtitle">{html.escape(page.subtitle or "")}</p>',
            '    <div class="blocks">',
            blocks,
            "    </div>",
            footer,
            f'    <div class="page-num">{page.page_number:02d}</div>',
            "  </section>",
        ]
    )


def _block_html(block: dict[str, Any]) -> str:
    block_type = str(block.get("type") or "text")
    if block_type == "evidence_cards":
        items = block.get("items") if isinstance(block.get("items"), list) else []
        cards = "\n".join(_evidence_card_html(item) for item in items if isinstance(item, dict))
        return f'      <div class="evidence-grid" data-block-type="evidence_cards">{cards}</div>'
    if block_type == "source_list":
        items = block.get("items") if isinstance(block.get("items"), list) else []
        rows = "\n".join(_source_item_html(item) for item in items if isinstance(item, dict))
        return f'      <ul class="sources" data-block-type="source_list">{rows}</ul>'
    text = str(block.get("text") or "")
    return (
        f'      <article class="block block-{_class_token(block_type)}" '
        f'data-block-type="{_attr(block_type)}"><p>{html.escape(text)}</p></article>'
    )


def _evidence_card_html(item: dict[str, Any]) -> str:
    return (
        '<article class="card">'
        f'<h2>{html.escape(str(item.get("claim", "")))}</h2>'
        f'<p>{html.escape(str(item.get("evidence", "")))}</p>'
        f'<small>{html.escape(str(item.get("source_title", "")))}</small>'
        "</article>"
    )


def _source_item_html(item: dict[str, Any]) -> str:
    title = html.escape(str(item.get("title", "")))
    date = html.escape(str(item.get("date") or ""))
    publisher = html.escape(str(item.get("publisher") or ""))
    return f"<li>{title} <span>{publisher} {date}</span></li>"


def _manifest(
    document: PageDocument,
    *,
    output: Path,
    manifest_path: Path,
    validation: ValidationReport,
) -> dict[str, Any]:
    return {
        "html_package_version": "0.1",
        "html_package_id": f"htmlpkg_{uuid4().hex[:16]}",
        "source_tool": TOOL_NAME,
        "renderer": "authoring_html_package",
        "renderer_contract": "authoring-html-package-v0",
        "html_path": str(output.resolve()),
        "manifest_path": str(manifest_path.resolve()),
        "page_document_id": document.page_document_id,
        "page_count": document.page_count,
        "javascript_enabled": False,
        "remote_assets_enabled": False,
        "asset_count": 0,
        "assets": [],
        "validation": validation.model_dump(mode="json"),
        "next_recommended_tools": ["pdf.render.html_package", "pdf.qa.visual_report"],
    }


def _validate(document: PageDocument) -> ValidationReport:
    checks = [
        ValidationCheck(
            name="html_package_manifest_valid",
            status="passed",
            details={"renderer_contract": "authoring-html-package-v0"},
        ),
        ValidationCheck(
            name="page_count_matches",
            status="passed" if document.page_count == len(document.pages) else "failed",
            details={"page_count": document.page_count, "pages": len(document.pages)},
        ),
        ValidationCheck(
            name="no_javascript",
            status="passed",
            details={"javascript_enabled": False},
        ),
        ValidationCheck(
            name="no_remote_assets",
            status="passed",
            details={"remote_assets_enabled": False},
        ),
    ]
    return ValidationReport(
        status="passed" if all(check.status == "passed" for check in checks) else "failed",
        checks=checks,
        page_count=document.page_count,
    )


def _reject_unsafe_blocks(document: PageDocument) -> None:
    for page in document.pages:
        for block in page.blocks:
            block_type = str(block.get("type") or "")
            if block_type in {"script", "javascript"}:
                raise AgentPDFException(
                    "unsafe_input_rejected",
                    "HTML package blocks must not contain JavaScript.",
                )
            src = str(block.get("src") or block.get("path") or block.get("image_path") or "")
            if src and _is_remote_asset(src):
                raise AgentPDFException(
                    "unsafe_input_rejected",
                    "HTML package assets must be local and self-contained.",
                    details={"asset_ref": src},
                )


def _reject_unsafe_design_tokens(document: PageDocument) -> None:
    tokens = document.design_tokens.model_dump(mode="json")
    for name, raw_value in tokens.items():
        value = str(raw_value)
        lowered = value.lower()
        if any(marker in lowered for marker in CSS_INJECTION_MARKERS):
            raise AgentPDFException(
                "unsafe_input_rejected",
                "Design tokens contain unsafe CSS or script markers.",
                details={"token": name},
            )
        if name in COLOR_TOKEN_FIELDS and not HEX_COLOR_RE.fullmatch(value):
            raise AgentPDFException(
                "unsafe_input_rejected",
                "Color design tokens must be #RGB or #RRGGBB hex values.",
                details={"token": name},
            )
        if name == "font_family" and any(marker in lowered for marker in FONT_FORBIDDEN_MARKERS):
            raise AgentPDFException(
                "unsafe_input_rejected",
                "Font family design token contains unsafe CSS markers.",
                details={"token": name},
            )


def _is_remote_asset(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https", "ftp", "file", "data", "javascript"}


def _document_title(document: PageDocument) -> str:
    return document.pages[0].title if document.pages else "AgentPDF Authoring"


def _stylesheet(tokens: dict[str, Any]) -> str:
    return f"""
    @page {{ size: 1280px 720px; margin: 0; }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: {tokens["font_family"]};
      color: {tokens["dark_color"]};
      background: {tokens["background_color"]};
    }}
    .slide {{
      position: relative;
      width: 1280px;
      min-height: 720px;
      padding: 64px 72px;
      break-after: page;
      background: linear-gradient(135deg, #ffffff 0%, {tokens["background_color"]} 100%);
      border-bottom: 1px solid #e5e7eb;
    }}
    .page-kicker {{
      margin: 0 0 14px;
      text-transform: uppercase;
      color: {tokens["accent_color"]};
      font-size: 14px;
      font-weight: 700;
    }}
    h1 {{
      max-width: 980px;
      margin: 0 0 16px;
      font-size: 44px;
      line-height: 1.06;
    }}
    h2 {{ margin: 0 0 8px; font-size: 20px; }}
    .subtitle {{ margin: 0 0 32px; max-width: 860px; font-size: 22px; color: #475569; }}
    .blocks {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }}
    .block, .card {{
      min-height: 130px;
      padding: 20px;
      border: 1px solid #d8dee9;
      border-radius: 8px;
      background: #ffffff;
    }}
    .block-hero {{ grid-column: span 2; font-size: 28px; color: {tokens["primary_color"]}; }}
    .evidence-grid {{ grid-column: 1 / -1; display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }}
    .sources {{ grid-column: 1 / -1; padding: 0; list-style: none; }}
    .sources li {{ padding: 12px 0; border-bottom: 1px solid #e5e7eb; }}
    footer {{ position: absolute; left: 72px; right: 140px; bottom: 32px; color: #64748b; font-size: 13px; }}
    .page-num {{ position: absolute; right: 72px; bottom: 28px; color: {tokens["primary_color"]}; font-weight: 700; }}
    """


def _attr(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def _class_token(value: object) -> str:
    text = str(value or "block")
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in text) or "block"


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"


def _failed_validation(
    message: str,
    *,
    code: str,
    payload: str,
    validation_error: ValidationError,
) -> ToolResult:
    error = AgentPDFException(
        code,
        message,
        retry_hint="Provide a valid local authoring payload and retry.",
        details={"payload": payload, "validation_errors": validation_error.errors(include_context=False)},
    ).to_error()
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool=TOOL_NAME,
        warnings=[message],
        error=error,
    )


def _validation_error_code(validation_error: ValidationError) -> str:
    for item in validation_error.errors(include_context=False):
        message = str(item.get("msg", "")).lower()
        location = ".".join(str(part) for part in item.get("loc", ())).lower()
        if "design_tokens" in location and (
            "unsafe" in message or "css" in message or "remote" in message or "hex" in message
        ):
            return "unsafe_input_rejected"
    return "authoring_invalid_page_document"
