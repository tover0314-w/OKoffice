from __future__ import annotations

import hashlib
import ipaddress
import re
import socket
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from okoffice.context.packet import _context_item_result, _web_citation_evidence
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import ToolResult


DEFAULT_MAX_BYTES = 1_000_000
MAX_CAPTURE_BYTES = 10_000_000


def capture_web_context(
    url: str,
    output_path: str | Path | None = None,
    *,
    label: str | None = None,
    role: str = "citation",
    context_item_id: str | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
    timeout_seconds: float = 10,
    allow_private_hosts: bool = False,
) -> ToolResult:
    tool = "pdf.context.web_capture"
    if max_bytes <= 0 or max_bytes > MAX_CAPTURE_BYTES:
        raise OKofficeException(
            "unsafe_input_rejected",
            f"max_bytes must be between 1 and {MAX_CAPTURE_BYTES}.",
        )
    if timeout_seconds <= 0 or timeout_seconds > 60:
        raise OKofficeException("unsafe_input_rejected", "timeout_seconds must be between 0 and 60.")

    citation_evidence = _web_citation_evidence(url, {"label": label})
    parsed = urlparse(str(citation_evidence["normalized_url"]))
    _validate_public_url_host(parsed.hostname, allow_private_hosts)

    request = Request(
        str(citation_evidence["normalized_url"]),
        headers={"User-Agent": "OKoffice-Local/0.1"},
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        final_url = str(getattr(response, "url", citation_evidence["normalized_url"]))
        final_parsed = urlparse(final_url)
        if final_parsed.scheme.lower() not in {"http", "https"}:
            raise OKofficeException("unsafe_input_rejected", "Web capture final URL must use http:// or https://.")
        if final_parsed.username or final_parsed.password:
            raise OKofficeException("unsafe_input_rejected", "Web capture final URL must not include credentials.")
        _validate_public_url_host(final_parsed.hostname, allow_private_hosts)
        raw = response.read(max_bytes + 1)

    truncated = len(raw) > max_bytes
    if truncated:
        raw = raw[:max_bytes]
    content_type = _response_content_type(response)
    text = _response_text(raw, content_type)
    text_preview = text[:12000]
    source_ref = context_item_id or "ctx_001"
    sha256 = hashlib.sha256(raw).hexdigest()
    title = label or _title_from_html(text) or str(citation_evidence.get("title") or citation_evidence["normalized_url"])

    fetched_evidence: dict[str, Any] = {
        **citation_evidence,
        "title": title[:300],
        "fetch_status": "fetched",
        "status_code": int(getattr(response, "status", 0) or 0),
        "final_url": final_url,
        "content_type": content_type,
        "bytes_read": len(raw),
        "max_bytes": max_bytes,
        "truncated": truncated,
        "sha256": sha256,
        "text_char_count": len(text),
        "text_preview": text_preview[:1000],
        "ssrf_policy": {
            "allowed_schemes": ["http", "https"],
            "allow_private_hosts": allow_private_hosts,
            "private_hosts": "allowed" if allow_private_hosts else "blocked",
            "credentials": "blocked",
        },
        "analysis_method": "local_http_fetch_text_v0",
    }
    item = {
        "context_item_id": source_ref,
        "type": "web_link",
        "role": role,
        "label": title,
        "source_ref": source_ref,
        "uri": fetched_evidence["normalized_url"],
        "metadata": {
            "scheme": fetched_evidence["scheme"],
            "domain": fetched_evidence["domain"],
            "char_count": len(text),
            "preview": text_preview[:240],
            "citation_evidence": fetched_evidence,
        },
        "content": {
            "text": text_preview,
            "citation": {
                "url": fetched_evidence["normalized_url"],
                "citation_evidence": fetched_evidence,
            },
            "web_capture": {
                "text": text_preview,
                "sha256": sha256,
                "content_type": content_type,
                "status_code": fetched_evidence["status_code"],
            },
        },
    }
    warnings = []
    if truncated:
        warnings.append(f"Web capture was truncated to {max_bytes} bytes.")
    return _context_item_result(
        tool=tool,
        item=item,
        output_path=output_path,
        next_recommended_tools=["pdf.context.packet", "pdf.compose.add_citation", "pdf.compose.from_context"],
        extra_usage={"web_capture": fetched_evidence},
        warnings=warnings,
    )


def _validate_public_url_host(hostname: str | None, allow_private_hosts: bool) -> None:
    if allow_private_hosts:
        return
    if not hostname:
        raise OKofficeException("unsafe_input_rejected", "URL must include a host.")
    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise OKofficeException("pdf_parse_failed", f"Unable to resolve URL host: {hostname}") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
            raise OKofficeException("unsafe_input_rejected", "Private or local URL hosts are blocked by default.")


def _response_content_type(response: object) -> str:
    headers = getattr(response, "headers", {})
    if hasattr(headers, "get"):
        return str(headers.get("Content-Type", "") or "")
    return ""


def _response_text(raw: bytes, content_type: str) -> str:
    encoding = _charset_from_content_type(content_type)
    decoded = raw.decode(encoding, errors="replace")
    if "html" in content_type.lower() or "<html" in decoded[:500].lower():
        return _html_to_text(decoded)
    return decoded


def _charset_from_content_type(content_type: str) -> str:
    match = re.search(r"charset=([A-Za-z0-9._-]+)", content_type, flags=re.IGNORECASE)
    return match.group(1) if match else "utf-8"


def _title_from_html(text: str) -> str | None:
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned:
            return cleaned[:300]
    return None


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"p", "br", "div", "section", "article", "h1", "h2", "h3", "li", "title"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)

    def text(self) -> str:
        return "\n".join(part.strip() for part in self.parts if part.strip())


def _html_to_text(raw_html: str) -> str:
    parser = _TextExtractor()
    parser.feed(raw_html)
    return parser.text()
