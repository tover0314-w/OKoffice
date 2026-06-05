from __future__ import annotations

from copy import deepcopy
from typing import Any


HTML_LAYER_BBOX_PRECISION = "estimated_dom_not_pdf_glyph_bbox"

DOCUMENT_RENDER_PROFILE: dict[str, Any] = {
    "profile_id": "browser_print_a4_v0",
    "engine": "browser_print",
    "fallback_renderer": "local_html_package_fallback",
    "page_size": "A4",
    "prefer_css_page_size": True,
    "print_background": True,
    "scale": 1.0,
    "margin": {"top": "16mm", "right": "16mm", "bottom": "16mm", "left": "16mm"},
    "timeout_ms": 30000,
    "wait_until": "load",
    "javascript_enabled": False,
    "remote_assets_enabled": False,
    "allow_private_hosts": False,
    "allowed_origins": [],
}

DECK_RENDER_PROFILE: dict[str, Any] = {
    **DOCUMENT_RENDER_PROFILE,
    "profile_id": "browser_print_deck_16x9_v0",
    "page_size": "1280px 720px",
    "margin": {"top": "0", "right": "0", "bottom": "0", "left": "0"},
}

RENDERER_CONSTRAINTS: dict[str, Any] = {
    "network": "blocked",
    "javascript": "blocked",
    "file_urls": "blocked",
    "asset_policy": "local_packaged_assets_only",
    "bbox_precision": HTML_LAYER_BBOX_PRECISION,
}

SUPPORTED_RENDERER_BACKENDS = {"auto", "local_html_package_fallback", "browser_chromium"}


def document_render_profile() -> dict[str, Any]:
    return deepcopy(DOCUMENT_RENDER_PROFILE)


def deck_render_profile() -> dict[str, Any]:
    return deepcopy(DECK_RENDER_PROFILE)


def renderer_constraints() -> dict[str, Any]:
    return deepcopy(RENDERER_CONSTRAINTS)


def local_html_package_fallback_backend(constraints: dict[str, Any] | None = None) -> dict[str, Any]:
    active_constraints = constraints or RENDERER_CONSTRAINTS
    return {
        "backend_id": "local_html_package_fallback",
        "engine": "reportlab_text_fallback",
        "source": "agentpdf.conversion.local.html_to_pdf",
        "is_browser_renderer": False,
        "fallback": True,
        "fallback_reason": "browser_renderer_worker_unavailable",
        "layout_fidelity": "text_layout_approximation",
        "network": str(active_constraints.get("network") or "blocked"),
        "javascript": str(active_constraints.get("javascript") or "blocked"),
        "file_urls": str(active_constraints.get("file_urls") or "blocked"),
    }


def browser_chromium_backend_unavailable(constraints: dict[str, Any] | None = None) -> dict[str, Any]:
    active_constraints = constraints or RENDERER_CONSTRAINTS
    return {
        "backend_id": "browser_chromium",
        "engine": "playwright_chromium",
        "source": "agentpdf.renderers.browser_worker",
        "is_browser_renderer": True,
        "fallback": False,
        "available": False,
        "missing_optional_dependency": "playwright",
        "install_extra": "browser-renderer",
        "layout_fidelity": "browser_print_unavailable",
        "network": str(active_constraints.get("network") or "blocked"),
        "javascript": str(active_constraints.get("javascript") or "blocked"),
        "file_urls": str(active_constraints.get("file_urls") or "blocked"),
    }


def browser_chromium_backend(constraints: dict[str, Any] | None = None) -> dict[str, Any]:
    active_constraints = constraints or RENDERER_CONSTRAINTS
    return {
        "backend_id": "browser_chromium",
        "engine": "playwright_chromium",
        "source": "agentpdf.renderers.browser_worker",
        "is_browser_renderer": True,
        "fallback": False,
        "available": True,
        "layout_fidelity": "browser_print",
        "network": str(active_constraints.get("network") or "blocked"),
        "javascript": str(active_constraints.get("javascript") or "blocked"),
        "file_urls": str(active_constraints.get("file_urls") or "blocked"),
    }
