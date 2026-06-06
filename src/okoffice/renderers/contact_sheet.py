"""Contact sheet renderer for OKoffice deck HTML previews.

Screenshots each slide from an HTML deck preview and composes them into
an N-up contact sheet image.  Falls back gracefully when Playwright or
a matching HTML preview is unavailable.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any
from uuid import uuid4

from okoffice.artifacts.store import build_artifact
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport
from okoffice.security.paths import resolve_input_path, resolve_output_path

CONTACT_SHEET_TOOL_NAME = "deck.validation.contact_sheet_render"
SLIDES_PER_ROW = 4
SLIDE_VIEWPORT_WIDTH = 1280
SLIDE_VIEWPORT_HEIGHT = 720
THUMBNAIL_WIDTH = 320
THUMBNAIL_HEIGHT = 180


def render_contact_sheet(
    html_path: str | Path,
    output_dir: str | Path,
    *,
    slides_per_row: int = SLIDES_PER_ROW,
) -> ToolResult:
    """Render per-slide screenshots and compose a contact sheet image."""
    try:
        source = resolve_input_path(html_path)
        out = resolve_output_path(output_dir)
    except Exception as exc:
        return _failed(
            OKofficeError(code="invalid_input", message=str(exc)),
        )

    if not source.exists():
        return _failed(
            OKofficeError(
                code="artifact_not_found",
                message=f"HTML deck preview not found: {source}",
                details={"html_path": str(source)},
            ),
        )

    out.mkdir(parents=True, exist_ok=True)

    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError:
        return _failed(
            OKofficeError(
                code="dependency_missing",
                message="Contact sheet rendering requires the optional Playwright dependency.",
                retry_hint="Install the browser-renderer extra and run `playwright install chromium`.",
            ),
            worker_status="not_available",
        )

    try:
        screenshots: list[Path] = []
        contact_sheet_path: Path | None = None
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            context = browser.new_context(
                viewport={"width": SLIDE_VIEWPORT_WIDTH, "height": SLIDE_VIEWPORT_HEIGHT},
                java_script_enabled=False,
            )
            context.route(
                "**/*",
                lambda route, request: _route_local_only(route, request, root=source.parent.resolve()),
            )
            page = context.new_page()
            page.goto(source.as_uri(), wait_until="load", timeout=30000)

            slide_elements = page.query_selector_all(".okoffice-slide")
            if not slide_elements:
                context.close()
                browser.close()
                return _failed(
                    OKofficeError(
                        code="render_failed",
                        message="No .okoffice-slide elements found in the HTML preview.",
                        details={"html_path": str(source)},
                    ),
                )

            for index, element in enumerate(slide_elements, start=1):
                screenshot_path = out / f"slide-{index:03d}.png"
                element.screenshot(path=str(screenshot_path))
                screenshots.append(screenshot_path)

            context.close()
            browser.close()

        contact_sheet_path = _compose_contact_sheet_html(
            screenshots,
            out / "contact-sheet.html",
            slides_per_row=slides_per_row,
        )

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            context = browser.new_context(viewport={"width": 1400, "height": 900})
            page = context.new_page()
            page.goto(contact_sheet_path.as_uri(), wait_until="load", timeout=15000)
            png_path = out / "contact-sheet.png"
            page.screenshot(path=str(png_path), full_page=True)
            context.close()
            browser.close()
            contact_sheet_path = png_path

    except Exception as exc:
        error_msg = str(exc)
        if "Executable doesn't exist" in error_msg or "playwright install" in error_msg:
            return _failed(
                OKofficeError(
                    code="dependency_missing",
                    message="Chromium browser executable is not installed for contact sheet rendering.",
                    retry_hint="Run `playwright install chromium`.",
                    details={"playwright_error": error_msg},
                ),
                worker_status="not_installed",
            )
        return _failed(
            OKofficeError(
                code="render_failed",
                message=f"Contact sheet rendering failed: {error_msg}",
                details={"html_path": str(source)},
            ),
        )

    artifacts = [build_artifact(s, CONTACT_SHEET_TOOL_NAME) for s in screenshots if s.exists()]
    if contact_sheet_path and contact_sheet_path.exists():
        artifacts.append(build_artifact(contact_sheet_path, CONTACT_SHEET_TOOL_NAME))

    checks = [
        ValidationCheck(
            name="html_preview_loaded",
            status="passed",
            details={"html_path": str(source), "slide_elements": len(screenshots)},
        ),
        ValidationCheck(
            name="slide_screenshots_captured",
            status="passed",
            details={"screenshot_count": len(screenshots)},
        ),
        ValidationCheck(
            name="contact_sheet_composed",
            status="passed" if contact_sheet_path and contact_sheet_path.exists() else "skipped",
            details={"contact_sheet_path": str(contact_sheet_path) if contact_sheet_path else None},
        ),
    ]

    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=CONTACT_SHEET_TOOL_NAME,
        artifacts=artifacts,
        validation=ValidationReport(status="passed", checks=checks),
        usage={
            "summary": {
                "html_path": str(source),
                "slide_count": len(screenshots),
                "rendered_contact_sheet": contact_sheet_path is not None and contact_sheet_path.exists(),
                "worker_status": "available",
            },
            "screenshots": [s.as_posix() for s in screenshots],
            "contact_sheet": {
                "path": str(contact_sheet_path) if contact_sheet_path else None,
                "slides_per_row": slides_per_row,
                "render_backend": "playwright_chromium",
            },
        },
        next_recommended_tools=["deck.validate.presentation", "office.bundle.export"],
    )


def _compose_contact_sheet_html(
    screenshots: list[Path],
    output_path: Path,
    *,
    slides_per_row: int = SLIDES_PER_ROW,
) -> Path:
    """Build an HTML page that arranges slide screenshots in a grid."""
    rows: list[list[str]] = []
    current_row: list[str] = []
    for screenshot in screenshots:
        data_uri = _image_to_data_uri(screenshot)
        current_row.append(data_uri)
        if len(current_row) >= slides_per_row:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)

    grid_html = ""
    for row in rows:
        cells = "\n".join(
            f'        <div class="cell"><img src="{src}" alt="slide" '
            f'style="width:{THUMBNAIL_WIDTH}px; height:{THUMBNAIL_HEIGHT}px; object-fit:contain;" /></div>'
            for src in row
        )
        grid_html += f'      <div class="row">\n{cells}\n      </div>\n'

    document = (
        "<!doctype html>\n"
        "<html><head><meta charset='utf-8'><title>Contact Sheet</title>\n"
        "<style>\n"
        "  body { margin: 16px; background: #f5f5f5; font-family: sans-serif; }\n"
        "  h1 { font-size: 18px; margin-bottom: 12px; }\n"
        "  .row { display: flex; gap: 8px; margin-bottom: 8px; }\n"
        "  .cell { border: 1px solid #ccc; background: #fff; }\n"
        "  img { display: block; }\n"
        "</style></head>\n"
        "<body>\n"
        f"  <h1>Contact Sheet ({len(screenshots)} slides)</h1>\n"
        f'{grid_html}'
        "</body></html>"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    return output_path


def _image_to_data_uri(path: Path) -> str:
    data = path.read_bytes()
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _route_local_only(route: Any, request: Any, *, root: Path) -> None:
    url = str(request.url)
    if url.startswith(("http://", "https://", "ftp://")):
        route.abort()
        return
    route.continue_()


def _failed(error: OKofficeError, *, worker_status: str = "error") -> ToolResult:
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool=CONTACT_SHEET_TOOL_NAME,
        error=error,
        warnings=[error.message],
        usage={
            "summary": {
                "rendered_contact_sheet": False,
                "worker_status": worker_status,
            },
        },
    )


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
