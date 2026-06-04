from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree


WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
SHEET_NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
DECK_NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}


def zip_names(path: Path) -> set[str]:
    with zipfile.ZipFile(path) as archive:
        return {name.replace("\\", "/") for name in archive.namelist()}


def read_xml(path: Path, member: str) -> ElementTree.Element | None:
    with zipfile.ZipFile(path) as archive:
        if member not in archive.namelist():
            return None
        return ElementTree.fromstring(archive.read(member))


def count_members(names: set[str], *, prefix: str, suffix: str = ".xml") -> int:
    return sum(1 for name in names if name.startswith(prefix) and name.endswith(suffix))


def sorted_members(names: set[str], *, prefix: str, suffix: str = ".xml") -> list[str]:
    return sorted(
        [name for name in names if name.startswith(prefix) and name.endswith(suffix)],
        key=_natural_key,
    )


def namespaced_attr(element: ElementTree.Element, namespace_uri: str, name: str) -> str | None:
    return element.get(f"{{{namespace_uri}}}{name}") or element.get(name)


def _natural_key(value: str) -> list[object]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", value)]
