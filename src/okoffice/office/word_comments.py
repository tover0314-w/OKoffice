from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from okoffice.office.shared import failed_result, job_id
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport
from okoffice.security.paths import resolve_input_path, resolve_output_path

TOOL_NAME = "word.comment.review"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"


def review_word_comments(
    input_path: str | Path,
    output_path: str | Path | None = None,
    resolve_ids: list[str] | None = None,
) -> ToolResult:
    try:
        path = resolve_input_path(input_path)
        comments, warnings = _extract_comments(path)

        if resolve_ids and output_path is not None:
            dest = resolve_output_path(output_path)
            _resolve_comments(path, dest, set(resolve_ids))
            return ToolResult(
                job_id=job_id(),
                status="succeeded",
                tool=TOOL_NAME,
                warnings=warnings,
                usage={
                    "total_comments": len(comments),
                    "resolved_count": len(resolve_ids),
                    "remaining_count": len(comments) - len(resolve_ids),
                },
                validation=ValidationReport(
                    status="passed",
                    checks=[
                        ValidationCheck(name="comments_parsed", status="passed", details={"count": len(comments)}),
                        ValidationCheck(name="comments_resolved", status="passed", details={"resolved": len(resolve_ids)}),
                    ],
                ),
                next_recommended_tools=["word.extract.comments", "word.patch.apply"],
            )

        return ToolResult(
            job_id=job_id(),
            status="succeeded",
            tool=TOOL_NAME,
            warnings=warnings,
            usage={
                "total_comments": len(comments),
                "comments": comments,
                "resolved_count": 0,
            },
            validation=ValidationReport(
                status="passed",
                checks=[
                    ValidationCheck(name="comments_parsed", status="passed", details={"count": len(comments)}),
                ],
            ),
            next_recommended_tools=["word.extract.comments", "word.patch.apply"],
        )
    except Exception as exc:
        return failed_result(TOOL_NAME, OKofficeError(code="comment_review_failed", message=str(exc)))


def _extract_comments(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    comments: list[dict[str, Any]] = []
    warnings: list[str] = []
    try:
        with zipfile.ZipFile(path) as z:
            if "word/comments.xml" not in z.namelist():
                return comments, ["No comments.xml found in document"]

            comments_xml = z.read("word/comments.xml")
            root = ET.fromstring(comments_xml)

            for comment_elem in root.findall(f"{W}comment"):
                cid = comment_elem.get(f"{W}id", "")
                author = comment_elem.get(f"{W}author", "")
                date_str = comment_elem.get(f"{W}date", "")
                initials = comment_elem.get(f"{W}initials", "")

                text_parts = []
                for t_elem in comment_elem.iter(f"{W}t"):
                    if t_elem.text:
                        text_parts.append(t_elem.text)

                reply_count = len(comment_elem.findall(f"{W}commentReference"))

                comments.append({
                    "id": cid,
                    "author": author,
                    "date": date_str,
                    "initials": initials,
                    "text": " ".join(text_parts),
                    "reply_count": reply_count,
                })
    except Exception as exc:
        warnings.append(f"Failed to parse comments: {exc}")
    return comments, warnings


def _resolve_comments(path: Path, dest: Path, resolve_ids: set[str]) -> None:
    with zipfile.ZipFile(path) as z_in:
        entries = z_in.namelist()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z_out:
            for name in entries:
                data = z_in.read(name)
                if name == "word/comments.xml":
                    data = _patch_comments_xml(data, resolve_ids)
                z_out.writestr(name, data)


def _patch_comments_xml(data: bytes, resolve_ids: set[str]) -> bytes:
    root = ET.fromstring(data)
    for comment in root.findall(f"{W}comment"):
        cid = comment.get(f"{W}id", "")
        if cid in resolve_ids:
            comment.set(f"{W}resolved", "1")
    ET.register_namespace("w", W_NS)
    return ET.tostring(root, encoding="unicode").encode("utf-8")
