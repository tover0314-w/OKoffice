from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import url2pathname
from uuid import uuid4

from okoffice.artifacts.store import build_artifact
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import ToolResult
from okoffice.security.paths import resolve_input_path, resolve_output_path
from okoffice.validation.pdf import validate_pdf


def browser_chromium_html_to_pdf(
    *,
    html_path: str | Path,
    manifest_path: str | Path,
    output_path: str | Path,
    render_profile: dict[str, Any],
    renderer_constraints: dict[str, Any],
) -> ToolResult:
    tool = "pdf.render.browser_chromium"
    source = resolve_input_path(html_path)
    manifest = resolve_input_path(manifest_path)
    output = resolve_output_path(output_path)
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise OKofficeException(
            "dependency_missing",
            "Chromium HTML rendering requires the optional Playwright dependency.",
            retry_hint="Install the browser-renderer extra and run `playwright install chromium`.",
            details={
                "requested_renderer_backend": "browser_chromium",
                "missing_optional_dependency": "playwright",
                "install_extra": "browser-renderer",
            },
        ) from exc

    package_root = manifest.parent.resolve()
    timeout_ms = int(render_profile.get("timeout_ms") or 30000)
    wait_until = str(render_profile.get("wait_until") or "load")
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(java_script_enabled=False)
            context.route(
                "**/*",
                lambda route, request: _route_packaged_request(route, request, package_root=package_root),
            )
            page = context.new_page()
            page.goto(source.as_uri(), wait_until=wait_until, timeout=timeout_ms)
            page.pdf(**_pdf_options(output, render_profile))
            context.close()
            browser.close()
    except PlaywrightError as exc:
        message = str(exc)
        if "Executable doesn't exist" in message or "playwright install" in message:
            raise OKofficeException(
                "dependency_missing",
                "Chromium browser executable is not installed for Playwright rendering.",
                retry_hint="Run `playwright install chromium` before using renderer_backend='browser_chromium'.",
                details={
                    "requested_renderer_backend": "browser_chromium",
                    "missing_optional_dependency": "playwright.chromium",
                    "install_extra": "browser-renderer",
                    "playwright_error": message,
                },
            ) from exc
        raise OKofficeException(
            "html_render_failed",
            "Chromium HTML package rendering failed.",
            details={
                "html_path": str(source),
                "manifest_path": str(manifest),
                "renderer_backend": "browser_chromium",
                "playwright_error": message,
            },
        ) from exc

    validation = validate_pdf(output)
    artifact = build_artifact(output, source_tool=tool)
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded" if validation.status == "passed" else "failed",
        tool=tool,
        artifacts=[artifact],
        validation=validation,
        warnings=[*validation.warnings],
        usage={
            "input": str(source),
            "manifest_path": str(manifest),
            "output": str(output),
            "renderer_backend": "browser_chromium",
            "render_profile": render_profile,
            "renderer_constraints": renderer_constraints,
            "network": "blocked",
            "javascript": "blocked",
            "asset_policy": renderer_constraints.get("asset_policy", "local_packaged_assets_only"),
        },
        next_recommended_tools=["pdf.validation.render_check", "pdf.validation.blank_page_check"],
    )


def _pdf_options(output: Path, render_profile: dict[str, Any]) -> dict[str, Any]:
    options: dict[str, Any] = {
        "path": str(output),
        "print_background": bool(render_profile.get("print_background", True)),
        "prefer_css_page_size": bool(render_profile.get("prefer_css_page_size", True)),
        "scale": float(render_profile.get("scale") or 1.0),
    }
    margin = render_profile.get("margin")
    if isinstance(margin, dict):
        options["margin"] = {str(key): str(value) for key, value in margin.items()}
    page_size = str(render_profile.get("page_size") or "A4")
    if " " in page_size:
        width, height = page_size.split(" ", 1)
        options["width"] = width
        options["height"] = height
    else:
        options["format"] = page_size
    return options


def _route_packaged_request(route: Any, request: Any, *, package_root: Path) -> None:
    parsed = urlparse(str(request.url))
    if parsed.scheme in {"http", "https", "ftp"}:
        route.abort()
        return
    if parsed.scheme == "file":
        request_path = Path(url2pathname(parsed.path)).resolve()
        if _is_relative_to(request_path, package_root):
            route.continue_()
            return
        route.abort()
        return
    route.continue_()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
