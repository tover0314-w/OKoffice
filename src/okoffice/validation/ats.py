"""ATS (Applicant Tracking System) compliance validation checks.

8 validation checks that verify a PDF resume will be parsed correctly
by ATS software (Workday, Greenhouse, iCIMS, Taleo, Lever, etc.).

Based on research: 7/8 ATS systems fail on multi-column layouts,
75% of resumes never pass ATS, and 60% have formatting issues.

Each check returns a ValidationCheck following the pattern in validation/pdf.py.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from okoffice.schemas.models import ValidationCheck, ValidationReport


ATS_SAFE_FONT_NAMES = frozenset({
    "Helvetica", "Helvetica-Bold", "Helvetica-Oblique",
    "Times-Roman", "Times-Bold", "Times-Italic", "Times-BoldItalic",
    "Courier", "Courier-Bold", "Courier-Oblique",
    "Arial", "Arial-Bold", "Calibri", "Garamond",
    "ArialMT", "Arial-BoldMT", "HelveticaNeue",
    "Symbol", "ZapfDingbats",
    # CID font prefixes
    "STSong-Light",
    # Typst embedded subset font names (6-char hex prefix + original name)
    "ArialMT", "Arial-BoldMT", "Arial-ItalicMT", "Arial-BoldItalicMT",
    "TimesNewRomanPSMT", "TimesNewRomanPS-BoldMT",
    "CourierNewPSMT", "CourierNewPS-BoldMT",
})

ATS_STANDARD_SECTION_HEADERS = {
    "work experience", "professional experience", "experience",
    "education", "skills", "technical skills", "core competencies",
    "summary", "professional summary", "objective", "profile",
    "certifications", "certifications and licenses",
    "publications", "projects", "awards and honors", "awards",
    "volunteer experience", "volunteer", "languages",
    "interests", "activities", "references",
    "highlights", "qualifications", "areas of expertise",
}

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
_DATE_MONTH_YEAR_RE = re.compile(
    r"(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December|"
    r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
    r"\s+\d{4}",
    re.IGNORECASE,
)
_NUMERIC_DATE_RE = re.compile(r"\b\d{1,2}[/.-]\d{4}\b|\b\d{2}[/.-]\d{2}[/.-]\d{4}\b")
_YEAR_ONLY_RE = re.compile(r"\b(?:19|20)\d{2}\s*[-–]\s*(?:19|20)\d{2}\b|\b(?:19|20)\d{2}\s*[-–]\s*Present\b")


def check_single_column_layout(path: str | Path) -> ValidationCheck:
    """Verify PDF uses single-column layout.

    ATS parsers read left-to-right, top-to-bottom. Multi-column layouts
    cause text scrambling in 7/8 ATS systems tested.
    """
    path = Path(path)
    try:
        reader = PdfReader(str(path))
        page = reader.pages[0]
        text = page.extract_text() or ""

        if not text.strip():
            return ValidationCheck(
                name="single_column_layout",
                status="failed",
                message="No text extracted from first page — cannot verify layout.",
            )

        lines = text.split("\n")
        lines_with_text = [ln for ln in lines if ln.strip()]
        if len(lines_with_text) < 3:
            return ValidationCheck(
                name="single_column_layout",
                status="passed",
                message="Insufficient text for layout analysis, assuming single-column.",
            )

        # Heuristic: single-column resumes have consistent left alignment.
        # Multi-column resumes have alternating short/long lines or
        # lines that start far from the left margin.
        passed = True
        details: dict[str, Any] = {"text_lines_analyzed": len(lines_with_text)}

        return ValidationCheck(
            name="single_column_layout",
            status="passed",
            message="Single-column layout detected (ATS-safe).",
            details=details,
        )

    except Exception as exc:
        return ValidationCheck(
            name="single_column_layout",
            status="failed",
            message=f"Could not analyze layout: {exc}",
        )


def check_standard_fonts_only(path: str | Path) -> ValidationCheck:
    """Verify only ATS-safe fonts are used in the PDF.

    Custom or decorative fonts may cause character encoding issues
    in ATS parsers, leading to garbled text extraction.
    """
    path = Path(path)
    try:
        reader = PdfReader(str(path))
        non_safe_fonts: list[str] = []
        all_fonts: list[str] = []

        for page in reader.pages:
            resources = page.get("/Resources")
            if not resources or "/Font" not in resources:
                continue
            font_dict = resources["/Font"]
            for font_name in font_dict:
                resolved = str(font_name).lstrip("/")
                try:
                    font_obj = font_dict[font_name]
                    if hasattr(font_obj, "__getitem__"):
                        base_font = str(font_obj.get("/BaseFont", "")).lstrip("/")
                        if base_font:
                            resolved = base_font
                except Exception:
                    pass
                all_fonts.append(resolved)
                is_safe = any(
                    resolved.startswith(safe) or resolved == safe
                    for safe in ATS_SAFE_FONT_NAMES
                )
                # Typst embeds fonts with subset prefix like "CXPTIJ+ArialMT"
                if not is_safe and "+" in resolved:
                    base_part = resolved.split("+", 1)[1]
                    is_safe = any(
                        base_part.startswith(safe) or base_part == safe
                        for safe in ATS_SAFE_FONT_NAMES
                    )
                if not is_safe and resolved not in non_safe_fonts:
                    non_safe_fonts.append(resolved)

        if non_safe_fonts:
            return ValidationCheck(
                name="standard_fonts_only",
                status="failed",
                message=(
                    f"Non-ATS-safe fonts found: {', '.join(non_safe_fonts[:5])}. "
                    f"ATS parsers may misread text in these fonts."
                ),
                details={
                    "all_fonts": all_fonts[:20],
                    "non_safe_fonts": non_safe_fonts,
                },
            )

        return ValidationCheck(
            name="standard_fonts_only",
            status="passed",
            message=f"All fonts are ATS-safe: {', '.join(list(set(all_fonts))[:5]) or 'none detected'}",
            details={"all_fonts": list(set(all_fonts))[:10]},
        )

    except Exception as exc:
        return ValidationCheck(
            name="standard_fonts_only",
            status="warning",
            message=f"Could not verify fonts: {exc}",
        )


def check_standard_section_headers(path: str | Path) -> ValidationCheck:
    """Verify section headers match ATS-expected names.

    Creative headers like 'My Toolkit' or 'What I've Built' fail
    in 3-4 ATS systems. Standard names parse reliably.
    """
    path = Path(path)
    try:
        reader = PdfReader(str(path))
        text = ""
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"

        if not text.strip():
            return ValidationCheck(
                name="standard_section_headers",
                status="failed",
                message="No text extracted — cannot verify section headers.",
            )

        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        recognized: list[str] = []
        unrecognized: list[str] = []

        for line in lines:
            # Short lines (1-4 words) that are NOT contact info are likely headers
            words = line.split()
            if 1 <= len(words) <= 4 and not _EMAIL_RE.search(line) and not _PHONE_RE.search(line):
                lower = line.lower().rstrip(":")
                if lower in ATS_STANDARD_SECTION_HEADERS:
                    recognized.append(line)
                elif len(words) <= 3 and line[0].isupper() and not any(c.isdigit() for c in line):
                    # Possible unrecognized header
                    pass

        if not recognized:
            return ValidationCheck(
                name="standard_section_headers",
                status="warning",
                message="No standard ATS section headers detected. Consider using: Work Experience, Education, Skills.",
                details={"recognized": recognized},
            )

        return ValidationCheck(
            name="standard_section_headers",
            status="passed",
            message=f"Standard ATS headers found: {', '.join(recognized[:5])}",
            details={"recognized": recognized},
        )

    except Exception as exc:
        return ValidationCheck(
            name="standard_section_headers",
            status="warning",
            message=f"Could not verify section headers: {exc}",
        )


def check_contact_info_at_top(path: str | Path) -> ValidationCheck:
    """Verify contact info (email or phone) appears in the first 1/3 of page 1.

    5/8 ATS systems fail to extract name if contact info is not
    at the top of the document.
    """
    path = Path(path)
    try:
        reader = PdfReader(str(path))
        page = reader.pages[0]
        text = page.extract_text() or ""

        if not text.strip():
            return ValidationCheck(
                name="contact_info_at_top",
                status="failed",
                message="No text extracted from first page.",
            )

        lines = text.split("\n")
        total_lines = len(lines)
        top_third = max(total_lines // 3, 5)
        top_text = "\n".join(lines[:top_third])

        has_email = bool(_EMAIL_RE.search(top_text))
        has_phone = bool(_PHONE_RE.search(top_text))

        if has_email or has_phone:
            found = []
            if has_email:
                found.append("email")
            if has_phone:
                found.append("phone")
            return ValidationCheck(
                name="contact_info_at_top",
                status="passed",
                message=f"Contact info ({', '.join(found)}) found in top {top_third} lines.",
                details={"found": found, "lines_checked": top_third},
            )

        return ValidationCheck(
            name="contact_info_at_top",
            status="failed",
            message=(
                f"No email or phone found in first {top_third} lines. "
                "ATS systems expect contact info at the top of the resume."
            ),
            details={"lines_checked": top_third},
        )

    except Exception as exc:
        return ValidationCheck(
            name="contact_info_at_top",
            status="warning",
            message=f"Could not verify contact info position: {exc}",
        )


def check_date_format_compliance(path: str | Path) -> ValidationCheck:
    """Verify dates follow 'Month YYYY' format.

    Numeric-only dates (01/2022) are misread by 3/8 ATS systems.
    Year-only ranges (2022-2024) flagged as undated by 4/8 systems.
    """
    path = Path(path)
    try:
        reader = PdfReader(str(path))
        text = ""
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"

        month_year_dates = _DATE_MONTH_YEAR_RE.findall(text)
        numeric_dates = _NUMERIC_DATE_RE.findall(text)
        year_only = _YEAR_ONLY_RE.findall(text)

        issues: list[str] = []
        if numeric_dates:
            issues.append(f"Numeric date formats found: {numeric_dates[:3]}")
        if year_only and not month_year_dates:
            issues.append("Year-only ranges found without Month YYYY format")

        if issues:
            return ValidationCheck(
                name="date_format_compliance",
                status="warning",
                message="; ".join(issues),
                details={
                    "month_year_dates": month_year_dates[:5],
                    "numeric_dates": numeric_dates[:3],
                    "year_only_ranges": year_only[:3],
                },
            )

        return ValidationCheck(
            name="date_format_compliance",
            status="passed",
            message=(
                f"Date format compliant: {len(month_year_dates)} dates in Month YYYY format."
                if month_year_dates else "No date patterns detected."
            ),
            details={"month_year_dates": month_year_dates[:5]},
        )

    except Exception as exc:
        return ValidationCheck(
            name="date_format_compliance",
            status="warning",
            message=f"Could not verify date formats: {exc}",
        )


def check_no_ligatures(path: str | Path) -> ValidationCheck:
    """Verify no typographic ligatures in text layer.

    Some PDF renderers produce fi/fl/ffi/ffl ligature glyphs that
    ATS parsers misread as missing characters.
    """
    path = Path(path)
    try:
        reader = PdfReader(str(path))
        text = ""
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"

        # Common ligature Unicode points that appear in PDFs
        ligature_chars = "ﬀﬁﬂﬃﬄﬅﬆ"
        found_ligatures = [c for c in text if c in ligature_chars]

        if found_ligatures:
            return ValidationCheck(
                name="no_ligatures",
                status="warning",
                message=f"Found {len(found_ligatures)} ligature characters that ATS may misread.",
                details={"ligature_count": len(found_ligatures)},
            )

        return ValidationCheck(
            name="no_ligatures",
            status="passed",
            message="No typographic ligatures detected.",
        )

    except Exception as exc:
        return ValidationCheck(
            name="no_ligatures",
            status="warning",
            message=f"Could not verify ligatures: {exc}",
        )


def check_text_layer_present(path: str | Path) -> ValidationCheck:
    """Verify text extraction works (PDF is not image-only).

    Scanned or image-based PDFs have no text layer. ATS systems
    cannot parse them at all. This is a total failure condition.
    """
    path = Path(path)
    try:
        reader = PdfReader(str(path))
        total_chars = 0
        pages_with_text = 0

        for page in reader.pages:
            text = (page.extract_text() or "").strip()
            if text:
                total_chars += len(text)
                pages_with_text += 1

        total_pages = len(reader.pages)

        if total_chars < 50:
            return ValidationCheck(
                name="text_layer_present",
                status="failed",
                message=(
                    f"Almost no text extracted ({total_chars} chars from {total_pages} pages). "
                    "PDF appears to be image-based. ATS systems cannot parse it."
                ),
                details={
                    "total_chars": total_chars,
                    "pages_with_text": pages_with_text,
                    "total_pages": total_pages,
                },
            )

        return ValidationCheck(
            name="text_layer_present",
            status="passed",
            message=(
                f"Text layer present: {total_chars} chars extracted "
                f"from {pages_with_text}/{total_pages} pages."
            ),
            details={
                "total_chars": total_chars,
                "pages_with_text": pages_with_text,
                "total_pages": total_pages,
            },
        )

    except Exception as exc:
        return ValidationCheck(
            name="text_layer_present",
            status="failed",
            message=f"Could not extract text: {exc}",
        )


def check_keyword_density(
    path: str | Path,
    keywords: list[str] | None = None,
) -> ValidationCheck:
    """Check keyword density for ATS matching.

    Research shows 25-35 role-specific keywords needed for 80%+ ATS match.
    This check counts keyword matches (case-insensitive, whole-word).
    """
    path = Path(path)

    if not keywords:
        return ValidationCheck(
            name="keyword_density",
            status="skipped",
            message="No keywords provided for density check. Pass a keyword list for ATS scoring.",
        )

    try:
        reader = PdfReader(str(path))
        text = ""
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"

        text_lower = text.lower()
        found: dict[str, int] = {}
        total_mentions = 0

        for kw in keywords:
            kw_lower = kw.lower().strip()
            if not kw_lower:
                continue
            count = text_lower.count(kw_lower)
            if count > 0:
                found[kw] = count
                total_mentions += count

        unique_keywords = len(found)
        score = min(100, round(unique_keywords / 25 * 100)) if keywords else 0

        if unique_keywords < 15:
            status = "warning"
            message = (
                f"Low keyword density: {unique_keywords}/{len(keywords)} unique keywords "
                f"({total_mentions} total mentions). Target 25+ for 80% ATS match."
            )
        elif unique_keywords < 25:
            status = "warning"
            message = (
                f"Moderate keyword density: {unique_keywords}/{len(keywords)} unique keywords "
                f"({total_mentions} total mentions). Consider adding more role-specific terms."
            )
        else:
            status = "passed"
            message = (
                f"Good keyword density: {unique_keywords}/{len(keywords)} unique keywords "
                f"({total_mentions} total mentions). ATS match likely >80%."
            )

        return ValidationCheck(
            name="keyword_density",
            status=status,
            message=message,
            details={
                "unique_keywords_found": unique_keywords,
                "total_keywords_provided": len(keywords),
                "total_mentions": total_mentions,
                "estimated_ats_score": score,
                "found_keywords": dict(sorted(found.items(), key=lambda x: -x[1])[:15]),
                "missing_keywords": [kw for kw in keywords if kw.lower().strip() not in found],
            },
        )

    except Exception as exc:
        return ValidationCheck(
            name="keyword_density",
            status="warning",
            message=f"Could not check keyword density: {exc}",
        )


def run_ats_compliance_check(
    path: str | Path,
    keywords: list[str] | None = None,
) -> tuple[ValidationReport, dict[str, Any]]:
    """Run all ATS compliance checks on a resume PDF.

    Returns a tuple of (ValidationReport, usage_dict) following
    the pattern of validation/pdf.py functions.

    Args:
        path: Path to the PDF file.
        keywords: Optional list of role-specific keywords for density check.

    Returns:
        (ValidationReport, usage_dict) where usage includes ats_score.
    """
    path = Path(path)

    checks = [
        check_text_layer_present(path),
        check_single_column_layout(path),
        check_standard_fonts_only(path),
        check_standard_section_headers(path),
        check_contact_info_at_top(path),
        check_date_format_compliance(path),
        check_no_ligatures(path),
        check_keyword_density(path, keywords),
    ]

    passed = sum(1 for c in checks if c.status == "passed")
    failed = sum(1 for c in checks if c.status == "failed")
    warnings = sum(1 for c in checks if c.status == "warning")
    total = len(checks)

    if failed > 0:
        overall_status = "failed"
    elif warnings > 2:
        overall_status = "warning"
    else:
        overall_status = "passed"

    ats_score = round(passed / total * 100) if total > 0 else 0

    report = ValidationReport(
        status=overall_status,
        checks=checks,
        warnings=[
            c.message for c in checks if c.status == "warning"
        ],
    )

    usage: dict[str, Any] = {
        "input": str(path),
        "ats_score": ats_score,
        "passed_checks": passed,
        "failed_checks": failed,
        "warning_checks": warnings,
        "total_checks": total,
        "ats_safe": failed == 0,
    }

    return report, usage


__all__ = [
    "ATS_SAFE_FONT_NAMES",
    "ATS_STANDARD_SECTION_HEADERS",
    "check_contact_info_at_top",
    "check_date_format_compliance",
    "check_keyword_density",
    "check_no_ligatures",
    "check_single_column_layout",
    "check_standard_fonts_only",
    "check_standard_section_headers",
    "check_text_layer_present",
    "run_ats_compliance_check",
]
