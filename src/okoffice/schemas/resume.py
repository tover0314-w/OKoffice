"""Structured resume data models with 9 entry types and auto-detection.

Inspired by RenderCV's entry type system. Every field includes
Field(description=...) for AI consumption — these descriptions flow
into the JSON Schema exposed as an MCP resource so agents can
self-discover the data model.
"""

from __future__ import annotations

import uuid
from uuid import uuid4

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field, TypeAdapter


class ContactInfo(BaseModel):
    """Contact information displayed at the top of a resume."""

    email: str | None = Field(
        None,
        description="Primary email address (e.g. 'alex@example.com')",
    )
    phone: str | None = Field(
        None,
        description="Phone number in display format (e.g. '+1 (555) 123-4567')",
    )
    location: str | None = Field(
        None,
        description="City, State/Country for display (e.g. 'San Francisco, CA')",
    )
    linkedin: str | None = Field(
        None,
        description="LinkedIn profile URL",
    )
    website: str | None = Field(
        None,
        description="Personal website or portfolio URL",
    )
    github: str | None = Field(
        None,
        description="GitHub profile URL",
    )


class ResumeDateRange(BaseModel):
    """Date range with ATS-compliant formatting."""

    start: str = Field(
        ...,
        description=(
            "Start date in 'Month YYYY' format (e.g. 'January 2022', 'Sep 2020'). "
            "ATS parsers read this reliably."
        ),
    )
    end: str | None = Field(
        None,
        description=(
            "End date in 'Month YYYY' format, or 'Present' for current positions. "
            "Leave empty for single-date entries."
        ),
    )


class ResumeEntryBase(BaseModel):
    """Base fields shared across all entry types."""

    entry_id: str = Field(
        default_factory=lambda: f"entry_{uuid4().hex[:8]}",
        description="Unique identifier for this entry (e.g. 'exp_1', 'edu_3')",
    )
    title: str = Field(
        ...,
        description="Primary title — job title, degree name, publication title, etc.",
    )
    organization: str | None = Field(
        None,
        description="Company, university, publisher, or institution name",
    )
    location: str | None = Field(
        None,
        description="City, State/Country (e.g. 'New York, NY')",
    )
    date_range: ResumeDateRange | None = Field(
        None,
        description="Start/end dates in Month YYYY format",
    )
    url: str | None = Field(
        None,
        description="Relevant URL (project link, publication DOI, etc.)",
    )
    highlights: list[str] = Field(
        default_factory=list,
        description="Bullet points or description lines for this entry",
    )


class ExperienceEntry(ResumeEntryBase):
    """Professional work experience entry.

    Auto-detected when: has 'organization' (company) + 'date_range' + 2+ highlights.
    """

    entry_type: Literal["experience"] = "experience"
    title: str = Field(
        ...,
        description="Job title (e.g. 'Senior Software Engineer', 'Product Manager')",
    )
    organization: str = Field(
        ...,
        description="Company or employer name",
    )


class EducationEntry(ResumeEntryBase):
    """Education entry (degree, certification, coursework).

    Auto-detected when: has 'gpa' or 'honors' field, or title contains degree keywords.
    """

    entry_type: Literal["education"] = "education"
    title: str = Field(
        ...,
        description="Degree or program name (e.g. 'B.S. Computer Science')",
    )
    organization: str = Field(
        ...,
        description="Institution name (e.g. 'Stanford University')",
    )
    gpa: str | None = Field(
        None,
        description="GPA if notable (e.g. '3.9/4.0')",
    )
    honors: list[str] = Field(
        default_factory=list,
        description="Honors, awards, or relevant coursework",
    )


class PublicationEntry(ResumeEntryBase):
    """Publication, paper, or speaking engagement.

    Auto-detected when: has 'authors' or 'venue' field.
    """

    entry_type: Literal["publication"] = "publication"
    title: str = Field(
        ...,
        description="Publication or talk title",
    )
    authors: str | None = Field(
        None,
        description="Author list (e.g. 'A. Smith, B. Jones, C. Lee')",
    )
    venue: str | None = Field(
        None,
        description="Journal, conference, or event name",
    )


class NormalEntry(ResumeEntryBase):
    """Standard content entry with title, organization, date, and bullets.

    Used for projects, volunteer work, or any entry that doesn't fit
    a more specific type. Default fallback type.
    """

    entry_type: Literal["normal"] = "normal"


class OneLineEntry(BaseModel):
    """Single line entry — certifications, languages, brief mentions.

    Auto-detected when: only has 'title', no other characteristic fields.
    """

    entry_id: str = Field(
        default_factory=lambda: f"entry_{uuid4().hex[:8]}",
        description="Unique identifier for this entry",
    )
    entry_type: Literal["one_line"] = "one_line"
    title: str = Field(
        ...,
        description="The single line of content (e.g. 'AWS Solutions Architect')",
    )
    detail: str | None = Field(
        None,
        description="Optional right-aligned detail (e.g. '2023', 'Native')",
    )


class BulletEntry(BaseModel):
    """Bullet-list only entry — skill groups, interest lists.

    Auto-detected when: has only 'highlights' list with no other characteristic fields.
    """

    entry_id: str = Field(
        default_factory=lambda: f"entry_{uuid4().hex[:8]}",
        description="Unique identifier for this entry",
    )
    entry_type: Literal["bullet"] = "bullet"
    highlights: list[str] = Field(
        ...,
        min_length=1,
        description="Required bullet items (e.g. ['Python', 'TypeScript', 'Go'])",
    )


class TextEntry(BaseModel):
    """Freeform paragraph text — professional summary, objective.

    Auto-detected when: has 'content' field.
    """

    entry_id: str = Field(
        default_factory=lambda: f"entry_{uuid4().hex[:8]}",
        description="Unique identifier for this entry",
    )
    entry_type: Literal["text"] = "text"
    content: str = Field(
        ...,
        description="Paragraph text content",
    )


class NumberedEntry(ResumeEntryBase):
    """Numbered list entry — patents, ordered achievements."""

    entry_type: Literal["numbered"] = "numbered"


class ReversedNumberedEntry(ResumeEntryBase):
    """Reverse-chronological numbered list — talks, publications by count."""

    entry_type: Literal["reversed_numbered"] = "reversed_numbered"


ResumeEntry = Annotated[
    Union[
        ExperienceEntry,
        EducationEntry,
        PublicationEntry,
        NormalEntry,
        OneLineEntry,
        BulletEntry,
        TextEntry,
        NumberedEntry,
        ReversedNumberedEntry,
    ],
    Field(discriminator="entry_type"),
]

resume_entry_adapter = TypeAdapter(ResumeEntry)


class ResumeSection(BaseModel):
    """A resume section containing entries of a specific type."""

    section_id: str = Field(
        ...,
        description="Unique section identifier (e.g. 'experience', 'education')",
    )
    title: str = Field(
        ...,
        description=(
            "Section header displayed to the reader. "
            "For ATS compatibility, use standard names: "
            "'Work Experience', 'Education', 'Skills', 'Certifications', "
            "'Projects', 'Publications', 'Languages', 'Volunteer Experience', "
            "'Awards', 'Summary', 'Professional Summary'."
        ),
    )
    entry_type: str = Field(
        ...,
        description="Expected entry type for entries in this section",
    )
    entries: list[ResumeEntry] = Field(
        default_factory=list,
        description="Ordered list of entries in this section",
    )
    order: int = Field(
        0,
        description="Display order — 0 appears first",
    )


class ResumeData(BaseModel):
    """Complete structured resume data model.

    This is the single source of truth for resume content.
    The rendering pipeline reads this model and applies design tokens
    and layout rules to produce the final PDF.
    """

    name: str = Field(
        ...,
        description="Full name of the candidate (e.g. 'Alexandra Chen')",
    )
    headline: str | None = Field(
        None,
        description="Professional headline or tagline (e.g. 'Senior Backend Engineer')",
    )
    photo_url: str | None = Field(
        None,
        description="Optional photo URL or local file path",
    )
    contact: ContactInfo = Field(
        default_factory=ContactInfo,
        description="Contact information displayed at the top of the resume",
    )
    sections: list[ResumeSection] = Field(
        default_factory=list,
        description="Ordered resume sections, each containing typed entries",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata (locale, custom fields, template hints)",
    )


# ---------- Auto-detection ----------

_DEGREE_KEYWORDS = {
    "bachelor", "master", "phd", "b.s.", "b.a.", "m.s.", "m.a.",
    "mba", "doctorate", "associate", "diploma", "certificate",
    "bsc", "msc", "ba", "ma", "btech", "mtech",
}

_CHARACTERISTIC_FIELDS: dict[str, set[str]] = {
    "text": {"content"},
    "publication": {"authors", "venue"},
    "education": {"gpa", "honors"},
    "experience": set(),
    "bullet": set(),
    "one_line": set(),
    "normal": set(),
    "numbered": set(),
    "reversed_numbered": set(),
}


def detect_entry_type(data: dict[str, Any]) -> str:
    """Auto-detect entry type from characteristic fields.

    Detection priority (first match wins):
    1. 'content' field present → text
    2. 'authors' or 'venue' present → publication
    3. 'gpa' or 'honors' present → education
    4. Title contains degree keywords → education
    5. Has 'organization' + 'date_range' + 2+ highlights → experience
    6. Only 'highlights' list (no title/org/date) → bullet
    7. Only 'title', no other characteristic fields → one_line
    8. Default → normal
    """
    fields = set(str(k).lower() for k in data.keys()) - {
        "entry_id", "entry_type", "model_config",
    }

    if "content" in fields:
        return "text"

    if "authors" in fields or "venue" in fields:
        return "publication"

    if "gpa" in fields or "honors" in fields:
        return "education"

    title = str(data.get("title", "")).lower()
    if any(kw in title for kw in _DEGREE_KEYWORDS):
        return "education"

    has_org = "organization" in fields or "company" in fields
    has_date = "date_range" in fields or "start_date" in fields
    highlights = data.get("highlights", [])
    has_many_highlights = isinstance(highlights, list) and len(highlights) >= 2

    if has_org and (has_date or has_many_highlights):
        return "experience"

    has_title = "title" in fields
    has_highlights = (
        "highlights" in fields
        and isinstance(highlights, list)
        and len(highlights) >= 1
    )
    has_extra = bool({"url", "location", "date_range", "start_date"} & fields)

    if has_highlights and not has_org and not has_date and not has_title:
        return "bullet"

    if has_title and not has_org and not has_date and not has_extra and not has_highlights:
        return "one_line"

    return "normal"


__all__ = [
    "ContactInfo",
    "ResumeData",
    "ResumeDateRange",
    "ResumeEntry",
    "ResumeEntryBase",
    "ResumeSection",
    "BulletEntry",
    "EducationEntry",
    "ExperienceEntry",
    "NormalEntry",
    "NumberedEntry",
    "OneLineEntry",
    "PublicationEntry",
    "ReversedNumberedEntry",
    "TextEntry",
    "detect_entry_type",
    "resume_entry_adapter",
]
