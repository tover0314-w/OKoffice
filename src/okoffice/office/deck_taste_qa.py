from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from okoffice.authoring.models import DesignTokens
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport
from okoffice.security.paths import resolve_input_path


REVIEW_TOOL_NAME = "deck.review.taste"


def check_color_contrast(tokens: DesignTokens) -> dict[str, Any]:
    score = 0.0
    issues: list[str] = []
    pairs = [
        ("primary_on_bg", tokens.primary_color, tokens.background_color),
        ("dark_on_bg", tokens.dark_color, tokens.background_color),
        ("accent_on_bg", tokens.accent_color, tokens.background_color),
    ]
    for name, fg, bg in pairs:
        ratio = _contrast_ratio(fg, bg)
        if ratio >= 4.5:
            score += 1.0
        elif ratio >= 3.0:
            score += 0.5
            issues.append(f"{name}: ratio {ratio:.1f} below WCAG AA (4.5)")
        else:
            issues.append(f"{name}: ratio {ratio:.1f} below WCAG AA (4.5)")
    max_score = len(pairs)
    return {"score": score / max_score, "max": 1.0, "issues": issues}


def check_typography_hierarchy(tokens: DesignTokens) -> dict[str, Any]:
    issues: list[str] = []
    score = 1.0
    if tokens.heading_size_px <= tokens.subtitle_size_px:
        issues.append("heading_size must be larger than subtitle_size")
        score -= 0.3
    if tokens.subtitle_size_px <= tokens.body_size_px:
        issues.append("subtitle_size must be larger than body_size")
        score -= 0.3
    if tokens.body_size_px <= tokens.kicker_size_px:
        issues.append("body_size must be larger than kicker_size")
        score -= 0.2
    if tokens.heading_line_height >= tokens.line_height:
        issues.append("heading_line_height should be tighter than body line_height")
        score -= 0.2
    return {"score": max(0, score), "max": 1.0, "issues": issues}


def check_whitespace_ratio(tokens: DesignTokens) -> dict[str, Any]:
    issues: list[str] = []
    score = 1.0
    slide_width = 1280
    slide_height = 720
    total_area = slide_width * slide_height
    padding_area = (2 * tokens.slide_padding_px * (slide_width + slide_height) - 4 * tokens.slide_padding_px ** 2)
    whitespace_ratio = padding_area / total_area if total_area > 0 else 0
    if whitespace_ratio < 0.08:
        issues.append(f"whitespace ratio {whitespace_ratio:.1%} below 8% minimum")
        score = whitespace_ratio / 0.08
    elif whitespace_ratio > 0.4:
        issues.append(f"whitespace ratio {whitespace_ratio:.1%} above 40% maximum")
        score = 0.4 / whitespace_ratio
    return {"score": score, "max": 1.0, "issues": issues, "whitespace_ratio": whitespace_ratio}


def check_slide_consistency(tokens: DesignTokens) -> dict[str, Any]:
    issues: list[str] = []
    score = 1.0
    if tokens.heading_font != tokens.body_font:
        if tokens.heading_font.split(",")[0].strip() == tokens.body_font.split(",")[0].strip():
            issues.append("heading and body fonts share the same primary face")
            score -= 0.1
    else:
        score -= 0.0
    size_ratios = tokens.heading_size_px / tokens.body_size_px if tokens.body_size_px > 0 else 1
    if size_ratios > 3.0:
        issues.append(f"heading/body size ratio {size_ratios:.1f} exceeds 3.0")
        score -= 0.3
    return {"score": max(0, score), "max": 1.0, "issues": issues}


def check_8_second_scan(tokens: DesignTokens) -> dict[str, Any]:
    issues: list[str] = []
    score = 1.0
    if tokens.heading_size_px < 24:
        issues.append("heading too small for 8-second scan")
        score -= 0.5
    if tokens.body_size_px > tokens.heading_size_px * 0.7:
        issues.append("body text too large relative to heading, reduces scanability")
        score -= 0.3
    return {"score": max(0, score), "max": 1.0, "issues": issues}


def check_rhythm_variation(slides: list[dict[str, Any]]) -> dict[str, Any]:
    if len(slides) < 3:
        return {"score": 1.0, "max": 1.0, "issues": []}
    layouts = [s.get("layout", "auto") for s in slides]
    unique = len(set(layouts))
    ratio = unique / len(layouts)
    issues: list[str] = []
    score = 1.0
    if ratio < 0.3:
        issues.append(f"only {unique} unique layouts across {len(layouts)} slides — deck looks monotonous")
        score = ratio / 0.3
    max_run = _longest_run(layouts)
    if max_run > 4:
        issues.append(f"same layout repeated {max_run} times consecutively")
        score -= 0.2
    return {"score": max(0, min(1, score)), "max": 1.0, "issues": issues}


def check_content_density(
    slides: list[dict[str, Any]],
    tokens: DesignTokens,
) -> dict[str, Any]:
    issues: list[str] = []
    violations = 0
    max_bullets = tokens.max_bullets_per_slide
    max_cards = tokens.max_cards_per_slide
    for i, slide in enumerate(slides):
        bullets = slide.get("bullets") or slide.get("body") or []
        if isinstance(bullets, str):
            bullets = [b.strip() for b in bullets.split("\n") if b.strip()]
        if len(bullets) > max_bullets:
            violations += 1
            if violations <= 3:
                issues.append(f"slide {i+1}: {len(bullets)} bullets exceeds max {max_bullets}")
        cards = slide.get("cards") or []
        if isinstance(cards, list) and len(cards) > max_cards:
            violations += 1
            if violations <= 3:
                issues.append(f"slide {i+1}: {len(cards)} cards exceeds max {max_cards}")
    score = 1.0
    if violations > 0:
        ratio = violations / len(slides)
        score = max(0, 1.0 - ratio)
    return {"score": score, "max": 1.0, "issues": issues, "violations": violations}


def check_shadow_restraint(tokens: DesignTokens) -> dict[str, Any]:
    issues: list[str] = []
    score = 1.0
    shadow = getattr(tokens, "shadow_restraint", "subtle")
    gradient = getattr(tokens, "gradient_sophistication", "subtle")
    if shadow == "none" and gradient == "flat":
        pass
    elif shadow == "medium" and gradient == "rich":
        issues.append("shadow_restraint=medium combined with gradient_sophistication=rich risks visual clutter")
        score -= 0.5
    if shadow == "medium":
        issues.append("medium shadows may compete with slide content — consider subtle")
        score -= 0.2
    return {"score": max(0, score), "max": 1.0, "issues": issues}


def check_template_consistency(
    used_templates: list[str],
) -> dict[str, Any]:
    if not used_templates:
        return {"score": 1.0, "max": 1.0, "issues": []}
    issues: list[str] = []
    unique = set(used_templates)
    if len(unique) > 3:
        issues.append(f"{len(unique)} distinct templates used — consider limiting to 2-3 for visual coherence")
    elif len(unique) == 1 and len(used_templates) > 6:
        issues.append("single template for all slides — consider section dividers or accent layouts")
    return {"score": max(0, 1.0 - 0.2 * max(0, len(unique) - 3)), "max": 1.0, "issues": issues}


def _longest_run(items: list[str]) -> int:
    if not items:
        return 0
    best = 1
    current = 1
    for i in range(1, len(items)):
        if items[i] == items[i - 1]:
            current += 1
            best = max(best, current)
        else:
            current = 1
    return best


def compute_taste_score(
    tokens: DesignTokens,
    *,
    slides: list[dict[str, Any]] | None = None,
    used_templates: list[str] | None = None,
) -> dict[str, Any]:
    contrast = check_color_contrast(tokens)
    typography = check_typography_hierarchy(tokens)
    whitespace = check_whitespace_ratio(tokens)
    consistency = check_slide_consistency(tokens)
    scan = check_8_second_scan(tokens)
    rhythm = check_rhythm_variation(slides) if slides else {"score": 1.0, "max": 1.0, "issues": []}
    density = check_content_density(slides, tokens) if slides else {"score": 1.0, "max": 1.0, "issues": []}
    shadow = check_shadow_restraint(tokens)
    template = check_template_consistency(used_templates or [])
    weights = {
        "contrast": 0.22,
        "typography": 0.15,
        "whitespace": 0.18,
        "consistency": 0.10,
        "scan": 0.08,
        "rhythm": 0.10,
        "density": 0.07,
        "shadow": 0.05,
        "template": 0.05,
    }
    checks_map = {
        "contrast": contrast,
        "typography": typography,
        "whitespace": whitespace,
        "consistency": consistency,
        "scan": scan,
        "rhythm": rhythm,
        "density": density,
        "shadow": shadow,
        "template": template,
    }
    total = sum(weights[name] * chk["score"] for name, chk in checks_map.items())
    all_issues: list[str] = []
    for name, chk in checks_map.items():
        for issue in chk.get("issues", []):
            all_issues.append(f"{name}: {issue}")
    return {
        "taste_score": round(total * 100),
        "checks": {
            "color_contrast": contrast,
            "typography_hierarchy": typography,
            "whitespace_ratio": whitespace,
            "slide_consistency": consistency,
            "eight_second_scan": scan,
            "rhythm_variation": rhythm,
            "content_density": density,
            "shadow_restraint": shadow,
            "template_consistency": template,
        },
        "issues": all_issues,
        "passing": total >= 0.7,
    }


def _luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    r = int(hex_color[0:2], 16) / 255
    g = int(hex_color[2:4], 16) / 255
    b = int(hex_color[4:6], 16) / 255
    return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)


def _linearize(c: float) -> float:
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _contrast_ratio(fg: str, bg: str) -> float:
    l1 = _luminance(fg)
    l2 = _luminance(bg)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def review_deck_taste(
    path: str | Path,
    *,
    html_preview_path: str | Path | None = None,
) -> ToolResult:
    """Review a deck for taste and design quality.

    Accepts either an HTML deck preview path (preferred) or a PPTX path
    with an adjacent HTML preview.  Runs static design-token scoring and
    returns a ToolResult with the taste score and specific issues.
    """
    try:
        source = resolve_input_path(path)
    except Exception as exc:
        return _review_failed(
            OKofficeError(code="invalid_input", message=str(exc)),
        )

    html_path = _resolve_taste_html(source, html_preview_path)
    if html_path is None:
        return _review_failed(
            OKofficeError(
                code="artifact_not_found",
                message="deck.review.taste requires an HTML deck preview (or PPTX with adjacent HTML).",
                details={"path": str(source)},
            ),
        )

    tokens = _load_design_tokens_from_html(html_path)
    if tokens is None:
        return _review_failed(
            OKofficeError(
                code="parse_failed",
                message="Could not extract design tokens from the HTML deck preview.",
                details={"html_path": str(html_path)},
            ),
        )

    taste_result = compute_taste_score(tokens)
    taste_score = taste_result["taste_score"]
    passing = taste_result["passing"]
    issues = taste_result["issues"]
    checks_detail = taste_result["checks"]

    warnings: list[str] = []
    if not passing:
        warnings.append(f"Taste score {taste_score}/100 is below the passing threshold of 70.")
    for issue in issues:
        warnings.append(issue)

    _new_check_names = ["rhythm_variation", "content_density", "shadow_restraint", "template_consistency"]
    review_checks = [
        ValidationCheck(
            name="taste_score",
            status="passed" if passing else "warning",
            details={"score": taste_score, "threshold": 70, "passing": passing},
        ),
        ValidationCheck(
            name="color_contrast",
            status="passed" if checks_detail["color_contrast"]["score"] >= 0.7 else "warning",
            details=checks_detail["color_contrast"],
        ),
        ValidationCheck(
            name="typography_hierarchy",
            status="passed" if checks_detail["typography_hierarchy"]["score"] >= 0.7 else "warning",
            details=checks_detail["typography_hierarchy"],
        ),
        ValidationCheck(
            name="whitespace_ratio",
            status="passed" if checks_detail["whitespace_ratio"]["score"] >= 0.7 else "warning",
            details=checks_detail["whitespace_ratio"],
        ),
        ValidationCheck(
            name="slide_consistency",
            status="passed" if checks_detail["slide_consistency"]["score"] >= 0.7 else "warning",
            details=checks_detail["slide_consistency"],
        ),
        ValidationCheck(
            name="eight_second_scan",
            status="passed" if checks_detail["eight_second_scan"]["score"] >= 0.7 else "warning",
            details=checks_detail["eight_second_scan"],
        ),
    ]
    for _cn in _new_check_names:
        _cd = checks_detail.get(_cn)
        if _cd is not None:
            review_checks.append(ValidationCheck(
                name=_cn,
                status="passed" if _cd["score"] >= 0.7 else "warning",
                details=_cd,
            ))

    return ToolResult(
        job_id=_review_job_id(),
        status="succeeded",
        tool=REVIEW_TOOL_NAME,
        validation=ValidationReport(
            status="passed" if passing else "warning",
            checks=review_checks,
            warnings=warnings,
        ),
        warnings=warnings,
        usage={
            "summary": {
                "html_path": str(html_path),
                "taste_score": taste_score,
                "passing": passing,
                "issue_count": len(issues),
            },
            "taste_result": taste_result,
        },
        next_recommended_tools=[
            "deck.validate.presentation",
            "deck.validation.contact_sheet",
            "office.bundle.export",
        ],
    )


def _resolve_taste_html(source: Path, html_preview_path: str | Path | None) -> Path | None:
    if html_preview_path is not None:
        candidate = Path(html_preview_path).expanduser().resolve()
        return candidate if candidate.exists() else None
    if source.suffix == ".html":
        return source
    sibling = source.with_suffix(".html")
    return sibling if sibling.exists() else None


def _load_design_tokens_from_html(html_path: Path) -> DesignTokens | None:
    manifest_path = html_path.with_suffix(".html-manifest.json")
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            theme_name = str(
                manifest.get("theme")
                or (manifest.get("design_tokens") or {}).get("theme")
                or "business_tech"
            )
            from okoffice.authoring.design import resolve_theme

            base = resolve_theme(theme_name)
            raw = manifest.get("design_tokens") or {}
            if raw:
                overrides = {k: v for k, v in raw.items() if v is not None}
                return base.model_copy(update=overrides)
            return base
        except (json.JSONDecodeError, Exception):
            pass
    return None


def _review_failed(error: OKofficeError) -> ToolResult:
    return ToolResult(
        job_id=_review_job_id(),
        status="failed",
        tool=REVIEW_TOOL_NAME,
        error=error,
        warnings=[error.message],
    )


def _review_job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
