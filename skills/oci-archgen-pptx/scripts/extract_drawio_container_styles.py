#!/usr/bin/env python3
"""Extract OCI draw.io grouping/container styles into a renderer style map."""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import urllib.parse
import zlib
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


DEFAULT_SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DRAWIO_LIBRARY = (
    Path.home() / "Downloads" / "OCI Style Guide for Drawio" / "OCI Library.xml"
)

STYLE_TITLES = {
    "region": "Physical - Grouping - OCI Region",
    "availability-domain": "Physical - Grouping - Availability Domain",
    "fault-domain": "Physical - Grouping - Fault Domain",
    "vcn": "Physical - Grouping - VCN",
    "subnet": "Physical - Grouping - Subnet",
    "compartment": "Physical - Grouping - Compartment",
    "tier": "Physical - Grouping - Tier",
}


def decode_raw_deflate_base64(value: str) -> str:
    raw = base64.b64decode(value + "=" * (-len(value) % 4))
    inflated = zlib.decompress(raw, -15).decode("utf-8")
    return urllib.parse.unquote(inflated)


def read_library(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    prefix = "<mxlibrary>"
    suffix = "</mxlibrary>"
    if not text.startswith(prefix) or not text.endswith(suffix):
        raise ValueError(f"not a draw.io mxlibrary file: {path}")
    return json.loads(text[len(prefix) : -len(suffix)])


def parse_style(style: str) -> dict[str, str]:
    values = {}
    for part in style.split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        values[key] = value
    return values


def clean_color(value: str | None) -> str | None:
    if not value or value.lower() == "none":
        return None
    return value.lstrip("#").upper()


def float_value(value: str | None, default: float) -> float:
    if value is None or value == "":
        return default
    return float(value)


def text_value(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", "", value)
    return urllib.parse.unquote(value).strip()


def first_styled_cell(xml: str) -> tuple[ET.Element, dict[str, str]]:
    root = ET.fromstring(xml)
    candidates = []
    for cell in root.findall(".//mxCell"):
        if cell.attrib.get("vertex") != "1":
            continue
        style = cell.attrib.get("style", "")
        parsed = parse_style(style)
        if parsed.get("strokeColor") or parsed.get("fillColor"):
            candidates.append((cell, parsed))
    if not candidates:
        raise ValueError("no styled vertex cell found")
    candidates.sort(key=lambda item: 1 if item[0].attrib.get("value") else 0, reverse=True)
    return candidates[0]


def find_item(items: list[dict[str, Any]], title: str) -> dict[str, Any]:
    for item in items:
        if item.get("title") == title:
            return item
    raise ValueError(f"draw.io library item not found: {title}")


def extract_style(items: list[dict[str, Any]], key: str, title: str) -> dict[str, Any]:
    item = find_item(items, title)
    xml = decode_raw_deflate_base64(str(item["xml"]))
    cell, style = first_styled_cell(xml)
    geometry = cell.find("mxGeometry")
    label = text_value(cell.attrib.get("value", "")) or title.split(" - ")[-1]
    arc_size = float_value(style.get("arcSize"), 0.0)

    return {
        "label": label,
        "source_title": title,
        "source_width": float(item.get("w") or 0),
        "source_height": float(item.get("h") or 0),
        "fill": clean_color(style.get("fillColor")),
        "line": clean_color(style.get("strokeColor")),
        "line_width": float_value(style.get("strokeWidth"), 1.0),
        "dash": "dash" if style.get("dashed") == "1" else None,
        "preset": "roundRect" if style.get("rounded") == "1" else "rect",
        "arc_size": arc_size,
        "rounding_adj": int(max(0, min(50000, arc_size * 200))) if style.get("rounded") == "1" else None,
        "font_color": clean_color(style.get("fontColor")) or "312D2A",
        "font_size": float_value(style.get("fontSize"), 12.0),
        "font_family": style.get("fontFamily") or "Oracle Sans",
        "align": style.get("align") or "left",
        "vertical_align": style.get("verticalAlign") or "top",
        "spacing_left": float_value(style.get("spacingLeft"), 0.0),
        "geometry": {
            "x": float_value(geometry.attrib.get("x") if geometry is not None else None, 0.0),
            "y": float_value(geometry.attrib.get("y") if geometry is not None else None, 0.0),
            "width": float_value(
                geometry.attrib.get("width") if geometry is not None else None,
                float(item.get("w") or 0),
            ),
            "height": float_value(
                geometry.attrib.get("height") if geometry is not None else None,
                float(item.get("h") or 0),
            ),
        },
    }


def build_style_map(items: list[dict[str, Any]], source: Path) -> dict[str, Any]:
    styles = {
        key: extract_style(items, key, title)
        for key, title in STYLE_TITLES.items()
    }
    return {
        "_metadata": {
            "source_drawio_library": str(source),
            "notes": [
                "Generated by scripts/extract_drawio_container_styles.py.",
                "Styles are derived from OCI draw.io Physical - Grouping entries.",
            ],
        },
        "styles": styles,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract OCI draw.io Physical - Grouping styles for PPTX containers."
    )
    parser.add_argument(
        "--library",
        default=str(DEFAULT_DRAWIO_LIBRARY),
        help="Path to OCI Library.xml from the OCI Style Guide for Drawio download.",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_SKILL_DIR / "references" / "container-style-map.json"),
        help="Output container style map JSON.",
    )
    args = parser.parse_args()

    library_path = Path(args.library)
    if not library_path.exists():
        print(f"[ERROR] draw.io library not found: {library_path}", file=sys.stderr)
        return 1

    try:
        items = read_library(library_path)
        style_map = build_style_map(items, library_path)
        write_json(Path(args.out), style_map)
    except Exception as exc:  # noqa: BLE001 - CLI should report a concise failure.
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    print(f"[OK] wrote container style map: {args.out}")
    print(f"[OK] extracted styles: {', '.join(STYLE_TITLES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
