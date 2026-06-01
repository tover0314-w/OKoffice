from __future__ import annotations

from pathlib import Path

from agentpdf.schemas.errors import AgentPDFException

SUSPICIOUS_CHARS = {"\x00", "<", ">", "|", "?", "*"}


def resolve_input_path(path: str | Path) -> Path:
    candidate = Path(path)
    _reject_suspicious_path(candidate)
    resolved = candidate.expanduser().resolve()
    if not resolved.exists() or not resolved.is_file():
        raise AgentPDFException("file_not_found", f"Input file not found: {candidate}")
    return resolved


def resolve_output_path(path: str | Path) -> Path:
    candidate = Path(path)
    _reject_suspicious_path(candidate)
    resolved = candidate.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def _reject_suspicious_path(path: Path) -> None:
    if any(part == ".." for part in path.parts):
        raise AgentPDFException("unsafe_input_rejected", f"Path traversal is not allowed: {path}")
    as_text = str(path)
    if any(char in as_text for char in SUSPICIOUS_CHARS):
        raise AgentPDFException("unsafe_input_rejected", f"Suspicious path rejected: {path}")
