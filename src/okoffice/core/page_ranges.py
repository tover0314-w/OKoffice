from __future__ import annotations

from okoffice.schemas.errors import OKofficeException


def parse_page_range(spec: str, total_pages: int) -> list[int]:
    normalized = spec.strip().lower()
    if total_pages < 1:
        raise OKofficeException("invalid_page_range", "PDF has no pages to select.")
    if normalized == "all":
        return list(range(total_pages))
    if normalized == "odd":
        return [index for index in range(total_pages) if (index + 1) % 2 == 1]
    if normalized == "even":
        return [index for index in range(total_pages) if (index + 1) % 2 == 0]
    if not normalized:
        raise OKofficeException("invalid_page_range", "Page range cannot be empty.")

    pages: list[int] = []
    for token in normalized.split(","):
        part = token.strip()
        if not part:
            raise OKofficeException("invalid_page_range", f"Invalid empty page range in {spec!r}.")
        if "-" in part:
            pages.extend(_parse_span(part, total_pages))
        else:
            pages.append(_parse_page_number(part, total_pages))

    deduped: list[int] = []
    seen: set[int] = set()
    for page in pages:
        if page not in seen:
            deduped.append(page)
            seen.add(page)
    return deduped


def _parse_span(part: str, total_pages: int) -> list[int]:
    raw_start, separator, raw_end = part.partition("-")
    if separator != "-" or not raw_start or not raw_end:
        raise OKofficeException("invalid_page_range", f"Invalid page span {part!r}.")
    start = _parse_page_number(raw_start, total_pages)
    end = _parse_page_number(raw_end, total_pages)
    if end < start:
        raise OKofficeException("invalid_page_range", f"Page span {part!r} is reversed.")
    return list(range(start, end + 1))


def _parse_page_number(raw: str, total_pages: int) -> int:
    if not raw.isdigit():
        raise OKofficeException("invalid_page_range", f"Invalid page number {raw!r}.")
    page = int(raw)
    if page < 1 or page > total_pages:
        raise OKofficeException(
            "invalid_page_range",
            f"Page {page} is outside the document page count of {total_pages}.",
        )
    return page - 1
