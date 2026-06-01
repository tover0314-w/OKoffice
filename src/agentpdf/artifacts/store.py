from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path

from pypdf import PdfReader

from agentpdf.schemas.models import Artifact


def build_artifact(path: str | Path, source_tool: str) -> Artifact:
    resolved = Path(path).resolve()
    data = resolved.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    mime_type = mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"
    page_count = _pdf_page_count(resolved) if mime_type == "application/pdf" else None
    return Artifact(
        artifact_id=f"art_{digest[:16]}",
        path=resolved,
        mime_type=mime_type,
        size_bytes=len(data),
        sha256=digest,
        source_tool=source_tool,
        page_count=page_count,
    )


def _pdf_page_count(path: Path) -> int | None:
    try:
        return len(PdfReader(path).pages)
    except Exception:
        return None
