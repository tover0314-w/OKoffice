from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


AuthoringFormat = Literal["html", "docx", "pptx", "markdown", "reportlab", "pdf_native"]
Confidence = Literal["high", "medium", "low"]
DeliverableKind = Literal["deck", "report", "whitepaper", "form", "existing_pdf_operation"]
SourceType = Literal["official", "report", "media", "blog", "paper", "documentation", "dataset", "other"]
HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
FONT_FORBIDDEN_MARKERS = ("<", ">", "{", "}", ";", "url(", "@import", "javascript:", "data:", "</style", "<script")


class AuthoringModel(BaseModel):
    pass


class AuthoringBrief(AuthoringModel):
    topic: str
    goal: str | None = None
    audience: str | None = None
    language: str = "en"
    page_count: int = 8
    deliverable: DeliverableKind = "deck"
    style: str = "business_research"
    research_required: bool = False
    citation_required: bool = False
    output_format: Literal["pdf", "html_package", "source_package"] = "pdf"
    constraints: dict[str, Any] = Field(default_factory=dict)

    @field_validator("topic")
    @classmethod
    def topic_must_not_be_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("topic must not be empty")
        return normalized

    @field_validator("page_count")
    @classmethod
    def page_count_must_be_local_mvp_size(cls, value: int) -> int:
        if value < 1:
            raise ValueError("page_count must be at least 1")
        if value > 80:
            raise ValueError("page_count must be at most 80 for local authoring MVP")
        return value


class RouteAlternative(AuthoringModel):
    authoring_format: AuthoringFormat
    fit: Literal["high", "medium", "low"]
    reason: str


class AuthoringRoute(AuthoringModel):
    authoring_route_id: str
    recommended_authoring_format: AuthoringFormat
    route_reason: str
    alternatives: list[RouteAlternative] = Field(default_factory=list)
    validation_required: list[str] = Field(default_factory=list)
    cloud_boundary: dict[str, Any] = Field(default_factory=dict)


class EvidenceCard(AuthoringModel):
    id: str
    claim: str
    evidence: str
    source_title: str
    source_url: str | None = None
    source_date: str | None = None
    publisher: str | None = None
    confidence: Confidence = "medium"
    usable_for: list[str] = Field(default_factory=list)

    @field_validator("id", "claim", "evidence", "source_title")
    @classmethod
    def required_text_must_not_be_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("field must not be empty")
        return normalized


class SourceCard(AuthoringModel):
    id: str
    title: str
    publisher: str | None = None
    source_date: str | None = None
    source_url: str | None = None
    source_type: SourceType = "other"
    reliability: Confidence = "medium"
    summary: str = ""
    key_points: list[str] = Field(default_factory=list)
    useful_for: list[str] = Field(default_factory=list)
    fetch_status: Literal["not_fetched"] = "not_fetched"

    @field_validator("id", "title")
    @classmethod
    def source_required_text_must_not_be_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("field must not be empty")
        return normalized

    @field_validator("summary")
    @classmethod
    def source_summary_must_be_string(cls, value: str) -> str:
        return value.strip()


class StoryboardPage(AuthoringModel):
    page_number: int
    page_type: str
    title: str
    core_claim: str
    layout: str
    evidence_refs: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @field_validator("page_number")
    @classmethod
    def page_number_must_be_positive(cls, value: int) -> int:
        if value < 1:
            raise ValueError("page_number must be at least 1")
        return value


class Storyboard(AuthoringModel):
    storyboard_id: str
    page_count: int
    pages: list[StoryboardPage]

    @model_validator(mode="after")
    def page_count_must_match_pages(self) -> Storyboard:
        if self.page_count != len(self.pages):
            raise ValueError("page_count must match pages length")
        return self


RhythmKind = Literal["anchor", "dense", "breathing"]
LayoutDensity = Literal["sparse", "moderate", "compact"]
ShadowRestraint = Literal["none", "subtle", "medium"]
GradientSophistication = Literal["flat", "subtle", "rich"]
BackgroundEffect = Literal["none", "gradient"]


@dataclass(frozen=True)
class SlideRhythm:
    rhythm_type: RhythmKind = "anchor"
    content_weight: float = 0.5
    whitespace_target: float = 0.20
    max_text_chars: int = 1200
    max_visual_elements: int = 9


class DesignTokens(AuthoringModel):
    theme: str = "business_tech"
    page_size: str = "16:9"
    font_family: str = "Noto Sans CJK SC, Arial, sans-serif"
    heading_font: str = "Noto Sans CJK SC, Arial, sans-serif"
    body_font: str = "Noto Sans CJK SC, Arial, sans-serif"
    display_font: str = "Noto Sans CJK SC, Georgia, serif"
    mono_font: str = "Courier New, Courier, monospace"
    primary_color: str = "#2563EB"
    accent_color: str = "#0F766E"
    warning_color: str = "#B45309"
    background_color: str = "#F8FAFC"
    dark_color: str = "#111827"
    heading_size_px: int = 36
    subtitle_size_px: int = 22
    body_size_px: int = 16
    caption_size_px: int = 10
    kicker_size_px: int = 11
    notes_size_px: int = 12
    line_height: float = 1.4
    heading_line_height: float = 1.2
    slide_padding_px: int = 48
    slide_gap_px: int = 28
    rhythm: RhythmKind = "anchor"
    layout_density: LayoutDensity = "moderate"
    max_bullets_per_slide: int = 6
    max_cards_per_slide: int = 6
    shadow_restraint: ShadowRestraint = "subtle"
    gradient_sophistication: GradientSophistication = "subtle"
    background_effect: BackgroundEffect = "none"

    @field_validator(
        "primary_color",
        "accent_color",
        "warning_color",
        "background_color",
        "dark_color",
    )
    @classmethod
    def color_tokens_must_be_hex(cls, value: str) -> str:
        if not HEX_COLOR_RE.fullmatch(value):
            raise ValueError("color tokens must be #RGB or #RRGGBB hex values")
        return value

    @field_validator("font_family", "heading_font", "body_font", "display_font", "mono_font")
    @classmethod
    def font_family_must_be_plain_stack(cls, value: str) -> str:
        lowered = value.lower()
        if any(marker in lowered for marker in FONT_FORBIDDEN_MARKERS):
            raise ValueError("font_family contains unsafe CSS, HTML, or remote markers")
        return value

    @field_validator("heading_size_px", "subtitle_size_px", "body_size_px", "caption_size_px", "kicker_size_px", "notes_size_px")
    @classmethod
    def font_size_must_be_positive(cls, value: int) -> int:
        if value < 6 or value > 120:
            raise ValueError("font size must be between 6 and 120 px")
        return value

    @field_validator("line_height", "heading_line_height")
    @classmethod
    def line_height_must_be_positive(cls, value: float) -> float:
        if value < 0.8 or value > 3.0:
            raise ValueError("line height must be between 0.8 and 3.0")
        return value

    @field_validator("max_bullets_per_slide", "max_cards_per_slide")
    @classmethod
    def max_elements_positive(cls, value: int) -> int:
        if value < 1 or value > 20:
            raise ValueError("max elements must be between 1 and 20")
        return value


Formality = Literal["high", "medium", "low"]
TemplateTrack = Literal["html", "svg", "both"]


class TemplateMetadata(AuthoringModel):
    template_id: str
    name: str
    mood: list[str] = Field(default_factory=list)
    tone: list[str] = Field(default_factory=list)
    formality: Formality = "medium"
    density: LayoutDensity = "moderate"
    scheme: list[str] = Field(default_factory=list)
    best_for: list[str] = Field(default_factory=list)
    avoid_for: list[str] = Field(default_factory=list)
    html_template_path: str | None = None
    svg_template_path: str | None = None
    track: TemplateTrack = "both"


class PageSpec(AuthoringModel):
    page_number: int
    layout: str
    title: str
    subtitle: str | None = None
    blocks: list[dict[str, Any]] = Field(default_factory=list)
    source_footer: str = ""
    evidence_refs: list[str] = Field(default_factory=list)

    @field_validator("page_number")
    @classmethod
    def page_number_must_be_positive(cls, value: int) -> int:
        if value < 1:
            raise ValueError("page_number must be at least 1")
        return value


class PageDocument(AuthoringModel):
    page_document_id: str
    page_count: int
    pages: list[PageSpec]
    design_tokens: DesignTokens = Field(default_factory=DesignTokens)

    @model_validator(mode="after")
    def page_count_must_match_pages(self) -> PageDocument:
        if self.page_count != len(self.pages):
            raise ValueError("page_count must match pages length")
        return self
