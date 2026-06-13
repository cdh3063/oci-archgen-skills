#!/usr/bin/env python3
"""Extract OCI draw.io mxlibrary stencil icons into SVG assets."""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import urllib.parse
import zlib
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape


DEFAULT_SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DRAWIO_LIBRARY = (
    Path.home() / "Downloads" / "OCI Style Guide for Drawio" / "OCI Library.xml"
)

TITLE_HINTS = {
    "bastion": ["Identity and Security - Bastion"],
    "compute": ["Compute - Virtual Machine VM"],
    "database": ["Database - Database System"],
    "dynamic-routing-gateway": ["Networking - Dynamic Routing Gateway DRG"],
    "exadata-database-service": ["Database - Exadata"],
    "internet-gateway": ["Networking - Internet Gateway"],
    "iam": ["Identity and Security - IAM Identity and Access Management"],
    "load-balancer": ["Networking - Load Balancer"],
    "nat-gateway": ["Networking - NAT Gateway"],
    "network-firewall": ["Identity and Security - Firewall"],
    "object-storage": ["Storage - Object Storage"],
    "audit": ["Observability and Management - Auditing"],
    "route-table": ["Networking - Route Table"],
    "security-list": ["Identity and Security - Security Lists"],
    "service-gateway": ["Networking - Service Gateway"],
    "subnet": ["Physical - Grouping - Subnet"],
    "virtual-cloud-network": ["Networking - Virtual Cloud Network VCN"],
}

REPLACE_SOURCE_TYPES = {"", "missing", "rendered-shape", "shape-label"}
NON_SERVICE_PREFIXES = ("Logical -", "Physical -")


@dataclass(frozen=True)
class DrawioItem:
    index: int
    title: str
    width: float
    height: float
    xml: str


@dataclass(frozen=True)
class StencilCell:
    x: float
    y: float
    width: float
    height: float
    fill: str
    stroke: str
    stencil: str


@dataclass(frozen=True)
class Match:
    icon_key: str
    score: float
    item: DrawioItem
    svg_path: Path
    stencil_count: int


def normalize(value: str) -> str:
    value = value.lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", normalize(value))
    return slug.strip("-") or "icon"


def service_label(title: str) -> str:
    return title.split(" - ", 1)[-1].replace("&amp;nbsp;", " ").replace("&nbsp;", " ")


def service_category(title: str) -> str:
    return title.split(" - ", 1)[0]


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"expected object JSON: {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def decode_raw_deflate_base64(value: str) -> str:
    raw = base64.b64decode(value + "=" * (-len(value) % 4))
    inflated = zlib.decompress(raw, -15).decode("utf-8")
    return urllib.parse.unquote(inflated)


def load_library(path: Path) -> list[DrawioItem]:
    text = path.read_text(encoding="utf-8")
    prefix = "<mxlibrary>"
    suffix = "</mxlibrary>"
    if not text.startswith(prefix) or not text.endswith(suffix):
        raise ValueError(f"not a draw.io mxlibrary file: {path}")

    raw_items = json.loads(text[len(prefix) : -len(suffix)])
    items = []
    for index, item in enumerate(raw_items):
        title = str(item.get("title") or "")
        if not title or not item.get("xml"):
            continue
        items.append(
            DrawioItem(
                index=index,
                title=title,
                width=float(item.get("w") or 0),
                height=float(item.get("h") or 0),
                xml=decode_raw_deflate_base64(str(item["xml"])),
            )
        )
    return items


def alias_patterns(alias_config: dict[str, Any]) -> dict[str, list[str]]:
    patterns = {}
    for icon_key, aliases in alias_config.get("aliases", {}).items():
        values = {normalize(icon_key), normalize(icon_key.replace("-", " "))}
        values.update(normalize(str(alias)) for alias in aliases)
        patterns[icon_key] = sorted(value for value in values if value)
    return patterns


def contains_phrase(text: str, phrase: str) -> bool:
    return f" {phrase} " in f" {text} "


def score_alias(label: str, patterns: list[str]) -> float:
    label_norm = normalize(label)
    if not label_norm:
        return 0.0
    best = 0.0
    for pattern in patterns:
        if label_norm == pattern:
            best = max(best, 1.0)
        elif contains_phrase(label_norm, pattern):
            best = max(best, 0.88)
        else:
            label_words = set(label_norm.split())
            pattern_words = set(pattern.split())
            if label_words and pattern_words:
                overlap = len(label_words & pattern_words) / len(pattern_words)
                if overlap >= 0.75:
                    best = max(best, 0.58)
    return best


def score_item(icon_key: str, item: DrawioItem, patterns: dict[str, list[str]]) -> float:
    hints = {normalize(title) for title in TITLE_HINTS.get(icon_key, [])}
    if normalize(item.title) in hints:
        return 1.0
    return score_alias(item.title, patterns.get(icon_key, []))


def parse_style(style: str) -> dict[str, str]:
    pairs = {}
    for part in style.split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        pairs[key] = value
    return pairs


def find_stencil_token(style: str) -> str:
    match = re.search(r"shape=stencil\(([^)]*)\)", style)
    return match.group(1) if match else ""


def float_attr(element: ET.Element | None, name: str, default: float = 0.0) -> float:
    if element is None:
        return default
    value = element.attrib.get(name)
    if value is None or value == "":
        return default
    return float(value)


def absolute_offsets(cells_by_id: dict[str, ET.Element], cell: ET.Element) -> tuple[float, float]:
    x = 0.0
    y = 0.0
    current: ET.Element | None = cell
    seen = set()
    while current is not None:
        cell_id = current.attrib.get("id")
        if cell_id in seen:
            break
        if cell_id:
            seen.add(cell_id)
        geometry = current.find("mxGeometry")
        x += float_attr(geometry, "x")
        y += float_attr(geometry, "y")
        parent = current.attrib.get("parent")
        current = cells_by_id.get(parent or "")
    return x, y


def collect_stencil_cells(item: DrawioItem) -> list[StencilCell]:
    root = ET.fromstring(item.xml)
    cells = root.findall(".//mxCell")
    cells_by_id = {cell.attrib.get("id", ""): cell for cell in cells}
    result: list[StencilCell] = []

    for cell in cells:
        if "value" in cell.attrib:
            continue
        style = cell.attrib.get("style", "")
        stencil = find_stencil_token(style)
        if not stencil:
            continue
        parsed = parse_style(style)
        fill = parsed.get("fillColor", "none")
        stroke = parsed.get("strokeColor", "none")
        if fill.lower() == "none" and stroke.lower() == "none":
            continue

        geometry = cell.find("mxGeometry")
        width = float_attr(geometry, "width")
        height = float_attr(geometry, "height")
        if width <= 0 or height <= 0:
            continue
        x, y = absolute_offsets(cells_by_id, cell)
        result.append(StencilCell(x, y, width, height, fill, stroke, stencil))

    return result


def path_data(path: ET.Element) -> str:
    commands = []
    for node in path:
        tag = node.tag.rsplit("}", 1)[-1]
        if tag == "move":
            commands.append(f"M {node.attrib['x']} {node.attrib['y']}")
        elif tag == "line":
            commands.append(f"L {node.attrib['x']} {node.attrib['y']}")
        elif tag == "curve":
            commands.append(
                "C {x1} {y1} {x2} {y2} {x3} {y3}".format(**node.attrib)
            )
        elif tag == "quad":
            commands.append("Q {x1} {y1} {x2} {y2}".format(**node.attrib))
        elif tag == "close":
            commands.append("Z")
    return " ".join(commands)


def color_attr(value: str) -> str:
    if not value or value.lower() == "none":
        return "none"
    if value.startswith("#"):
        return value
    return f"#{value}"


def cell_to_svg_paths(cell: StencilCell, min_x: float, min_y: float) -> list[str]:
    stencil_xml = decode_raw_deflate_base64(cell.stencil)
    root = ET.fromstring(stencil_xml)
    fill = escape(color_attr(cell.fill))
    stroke = escape(color_attr(cell.stroke))
    transform = (
        f"translate({cell.x - min_x:.4f} {cell.y - min_y:.4f}) "
        f"scale({cell.width / 100:.6f} {cell.height / 100:.6f})"
    )
    paths = []
    for path in root.findall(".//path"):
        data = path_data(path)
        if not data:
            continue
        paths.append(
            f'<path d="{escape(data)}" fill="{fill}" stroke="{stroke}" '
            'fill-rule="evenodd" clip-rule="evenodd" '
            f'transform="{transform}"/>'
        )
    return paths


def item_to_svg(item: DrawioItem) -> tuple[str, int]:
    cells = collect_stencil_cells(item)
    if not cells:
        raise ValueError(f"no drawable stencil cells: {item.title}")

    min_x = min(cell.x for cell in cells)
    min_y = min(cell.y for cell in cells)
    max_x = max(cell.x + cell.width for cell in cells)
    max_y = max(cell.y + cell.height for cell in cells)
    width = max_x - min_x
    height = max_y - min_y
    side = max(width, height) * 1.08
    view_x = -(side - width) / 2
    view_y = -(side - height) / 2

    paths = []
    for cell in cells:
        paths.extend(cell_to_svg_paths(cell, min_x, min_y))
    body = "\n  ".join(paths)
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'width="512" height="512" '
        f'viewBox="{view_x:.4f} {view_y:.4f} {side:.4f} {side:.4f}" '
        'preserveAspectRatio="xMidYMid meet" role="img" '
        f'aria-label="{escape(item.title)}">\n  {body}\n</svg>\n'
    )
    return svg, len(cells)


def select_matches(
    items: list[DrawioItem],
    patterns: dict[str, list[str]],
    icon_keys: list[str],
) -> list[tuple[str, float, DrawioItem]]:
    matches = []
    for icon_key in icon_keys:
        scored = [
            (score_item(icon_key, item, patterns), item)
            for item in items
            if collect_stencil_cells(item)
        ]
        scored = [(score, item) for score, item in scored if score >= 0.58]
        if not scored:
            continue
        scored.sort(
            key=lambda pair: (
                pair[0],
                normalize(pair[1].title) in {normalize(t) for t in TITLE_HINTS.get(icon_key, [])},
                -pair[1].index,
            ),
            reverse=True,
        )
        score, item = scored[0]
        matches.append((icon_key, score, item))
    return matches


def preferred_keys_by_title() -> dict[str, str]:
    result = {}
    for icon_key, titles in TITLE_HINTS.items():
        for title in titles:
            result[normalize(title)] = icon_key
    return result


def select_all_service_matches(items: list[DrawioItem]) -> list[tuple[str, float, DrawioItem]]:
    preferred = preferred_keys_by_title()
    preferred_keys = set(preferred.values())
    used: dict[str, str] = {}
    matches: list[tuple[str, float, DrawioItem]] = []

    for item in items:
        if item.title.startswith(NON_SERVICE_PREFIXES):
            continue
        if not collect_stencil_cells(item):
            continue

        title_norm = normalize(item.title)
        icon_key = preferred.get(title_norm)
        if not icon_key:
            base_key = slugify(service_label(item.title))
            if base_key in preferred_keys:
                base_key = slugify(f"{service_category(item.title)} {service_label(item.title)}")
            icon_key = base_key

        if icon_key in used:
            icon_key = slugify(f"{icon_key} drawio {item.index}")
        used[icon_key] = item.title
        matches.append((icon_key, 1.0, item))

    return matches


def write_svgs(
    selected: list[tuple[str, float, DrawioItem]],
    out_dir: Path,
    skill_dir: Path,
) -> list[Match]:
    out_dir.mkdir(parents=True, exist_ok=True)
    matches = []
    for icon_key, score, item in selected:
        svg, stencil_count = item_to_svg(item)
        svg_path = out_dir / f"{slugify(icon_key)}.svg"
        svg_path.write_text(svg, encoding="utf-8")
        matches.append(
            Match(
                icon_key=icon_key,
                score=score,
                item=item,
                svg_path=svg_path.relative_to(skill_dir),
                stencil_count=stencil_count,
            )
        )
    return matches


def should_replace(entry: object, replace_existing: bool) -> bool:
    if replace_existing:
        return True
    if not isinstance(entry, dict):
        return True
    source_type = str(entry.get("source_type") or "")
    asset_path = str(entry.get("asset_path") or "")
    return source_type in REPLACE_SOURCE_TYPES or not asset_path


def merge_icon_map(
    icon_map: dict[str, Any],
    matches: list[Match],
    alias_config: dict[str, Any],
    source_library: Path,
    replace_existing: bool,
    asset_format: str,
) -> list[str]:
    updated = []
    for match in matches:
        entry = icon_map.get(match.icon_key, {})
        if not should_replace(entry, replace_existing):
            continue
        if not isinstance(entry, dict):
            entry = {}
        svg_asset = str(match.svg_path)
        if asset_format == "png":
            asset_path = svg_asset.replace(".svg", ".drawio.png")
            source_type = "drawio-raster"
            extra = {
                "source_drawio_svg": svg_asset,
                "raster_source": {
                    "tool": "qlmanage",
                    "source_svg": svg_asset,
                    "size_px": 512,
                },
            }
        else:
            asset_path = svg_asset
            source_type = "drawio-vector"
            extra = {}
        icon_map[match.icon_key] = {
            **entry,
            "label": entry.get("label") or service_label(match.item.title),
            "aliases": alias_config.get("aliases", {}).get(match.icon_key, []),
            "asset_path": asset_path,
            "source_type": source_type,
            "source_drawio_library": str(source_library),
            "source_drawio_title": match.item.title,
            "source_drawio_index": match.item.index,
            "confidence": round(match.score, 4),
            "match_source": {
                "drawio_title": match.item.title,
                "item_width": match.item.width,
                "item_height": match.item.height,
                "stencil_count": match.stencil_count,
            },
            **extra,
        }
        updated.append(match.icon_key)

    metadata = icon_map.setdefault("_metadata", {})
    if isinstance(metadata, dict):
        notes = list(metadata.get("notes") or [])
        note = (
            "drawio-vector entries were extracted from OCI Library.xml "
            "by scripts/extract_drawio_icons.py."
        )
        if note not in notes:
            notes.append(note)
        metadata["notes"] = notes
        metadata["source_drawio_library"] = str(source_library)
        metadata["drawio_vector_assets"] = sorted(
            key
            for key, value in icon_map.items()
            if isinstance(value, dict) and value.get("source_type") == "drawio-vector"
        )
        metadata["drawio_raster_assets"] = sorted(
            key
            for key, value in icon_map.items()
            if isinstance(value, dict) and value.get("source_type") == "drawio-raster"
        )
        if "rendered_shape_assets" in metadata:
            metadata["rendered_shape_assets"] = sorted(
                key
                for key, value in icon_map.items()
                if isinstance(value, dict) and value.get("source_type") == "rendered-shape"
            )
        required = list(alias_config.get("required_keys", []))
        metadata["missing_required"] = [key for key in required if key not in icon_map]
        metadata["missing_required_assets"] = [
            key
            for key in required
            if not isinstance(icon_map.get(key), dict)
            or not str(icon_map[key].get("asset_path") or "")
        ]
        metadata["shape_only_required"] = [
            key
            for key in required
            if isinstance(icon_map.get(key), dict)
            and icon_map[key].get("source_type") == "shape-label"
        ]
    return updated


def build_inventory(matches: list[Match], items: list[DrawioItem], source_library: Path) -> dict[str, Any]:
    return {
        "_metadata": {
            "source_drawio_library": str(source_library),
            "item_count": len(items),
            "matched_icon_count": len(matches),
            "notes": [
                "draw.io library entries are compressed mxGraph XML.",
                "OCI icons are vector stencil paths, not embedded data:image assets.",
            ],
        },
        "matches": [
            {
                "icon_key": match.icon_key,
                "score": round(match.score, 4),
                "title": match.item.title,
                "item_index": match.item.index,
                "item_width": match.item.width,
                "item_height": match.item.height,
                "asset_path": str(match.svg_path),
                "stencil_count": match.stencil_count,
            }
            for match in sorted(matches, key=lambda item: item.icon_key)
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract SVG icon assets from Oracle's OCI draw.io mxlibrary."
    )
    parser.add_argument(
        "--library",
        default=str(DEFAULT_DRAWIO_LIBRARY),
        help="Path to OCI Library.xml from the OCI Style Guide for Drawio download.",
    )
    parser.add_argument(
        "--aliases",
        default=str(DEFAULT_SKILL_DIR / "references" / "icon-aliases.json"),
        help="Path to icon aliases JSON.",
    )
    parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_SKILL_DIR / "assets" / "extracted-icons"),
        help="Directory for generated SVG files.",
    )
    parser.add_argument(
        "--map",
        default=str(DEFAULT_SKILL_DIR / "references" / "icon-map.json"),
        help="Icon map JSON to merge draw.io vector assets into.",
    )
    parser.add_argument(
        "--inventory",
        default=str(DEFAULT_SKILL_DIR / "references" / "drawio-icon-inventory.json"),
        help="Path for generated draw.io inventory JSON.",
    )
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Replace existing image mappings instead of only missing/shape-only entries.",
    )
    parser.add_argument(
        "--all-services",
        action="store_true",
        help="Extract every drawable non-Logical/non-Physical draw.io service icon.",
    )
    parser.add_argument(
        "--asset-format",
        choices=("svg", "png"),
        default="svg",
        help="Register extracted icons as SVG vectors or qlmanage PNG fallbacks.",
    )
    parser.add_argument(
        "--keys",
        nargs="*",
        help="Optional icon keys to extract. Defaults to all alias keys.",
    )
    args = parser.parse_args()

    skill_dir = DEFAULT_SKILL_DIR
    library_path = Path(args.library)
    alias_path = Path(args.aliases)
    map_path = Path(args.map)
    out_dir = Path(args.out_dir)
    inventory_path = Path(args.inventory)

    if not library_path.exists():
        print(f"[ERROR] draw.io library not found: {library_path}", file=sys.stderr)
        return 1
    if not alias_path.exists():
        print(f"[ERROR] alias config not found: {alias_path}", file=sys.stderr)
        return 1
    if not map_path.exists():
        print(f"[ERROR] icon map not found: {map_path}", file=sys.stderr)
        return 1

    alias_config = read_json(alias_path)
    icon_map = read_json(map_path)
    patterns = alias_patterns(alias_config)
    icon_keys = args.keys or sorted(alias_config.get("aliases", {}).keys())

    try:
        items = load_library(library_path)
        selected = (
            select_all_service_matches(items)
            if args.all_services
            else select_matches(items, patterns, icon_keys)
        )
        matches = write_svgs(selected, out_dir, skill_dir)
        updated = merge_icon_map(
            icon_map,
            matches,
            alias_config,
            library_path,
            args.replace_existing,
            args.asset_format,
        )
        write_json(map_path, icon_map)
        write_json(inventory_path, build_inventory(matches, items, library_path))
    except Exception as exc:  # noqa: BLE001 - CLI should report a concise failure.
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    print(f"[OK] wrote SVG assets: {out_dir}")
    print(f"[OK] wrote inventory: {inventory_path}")
    print(f"[OK] matched icons: {len(matches)}")
    if updated:
        print(f"[OK] updated icon map: {', '.join(sorted(updated))}")
    else:
        print("[OK] icon map unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
