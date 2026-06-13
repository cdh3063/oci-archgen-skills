#!/usr/bin/env python3
import argparse
import json
import math
import posixpath
import re
import shutil
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

DEFAULT_SKILL_DIR = Path(__file__).resolve().parents[1]
EMU_PER_INCH = 914400


def normalize(value: str) -> str:
    value = value.lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", normalize(value))
    return slug.strip("-") or "icon"


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def rel_target_to_part(source_part: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join(posixpath.dirname(source_part), target))


def parse_relationships(package: zipfile.ZipFile, slide_part: str) -> dict[str, str]:
    slide_name = posixpath.basename(slide_part)
    rels_part = f"{posixpath.dirname(slide_part)}/_rels/{slide_name}.rels"
    if rels_part not in package.namelist():
        return {}

    root = ET.fromstring(package.read(rels_part))
    rels: dict[str, str] = {}
    for rel in root.findall("rel:Relationship", NS):
        rel_id = rel.attrib.get("Id")
        target = rel.attrib.get("Target")
        if rel_id and target:
            rels[rel_id] = rel_target_to_part(slide_part, target)
    return rels


def text_from_element(element: ET.Element) -> str:
    parts = [node.text or "" for node in element.findall(".//a:t", NS)]
    return " ".join(part.strip() for part in parts if part and part.strip()).strip()


def c_nv_name(element: ET.Element) -> tuple[str, str]:
    node = element.find(".//p:cNvPr", NS)
    if node is None:
        return "", ""
    return node.attrib.get("name", ""), node.attrib.get("descr", "")


def xfrm_box(element: ET.Element) -> dict[str, Optional[float]]:
    xfrm = element.find(".//a:xfrm", NS)
    if xfrm is None:
        return {"x": None, "y": None, "cx": None, "cy": None}

    off = xfrm.find("a:off", NS)
    ext = xfrm.find("a:ext", NS)
    x = float(off.attrib.get("x", "0")) if off is not None else None
    y = float(off.attrib.get("y", "0")) if off is not None else None
    cx = float(ext.attrib.get("cx", "0")) if ext is not None else None
    cy = float(ext.attrib.get("cy", "0")) if ext is not None else None
    return {"x": x, "y": y, "cx": cx, "cy": cy}


def center(box: dict[str, Optional[float]]) -> Optional[tuple[float, float]]:
    if box["x"] is None or box["y"] is None or box["cx"] is None or box["cy"] is None:
        return None
    return (float(box["x"]) + float(box["cx"]) / 2, float(box["y"]) + float(box["cy"]) / 2)


def distance(a: Optional[tuple[float, float]], b: Optional[tuple[float, float]]) -> Optional[float]:
    if a is None or b is None:
        return None
    return math.hypot(a[0] - b[0], a[1] - b[1])


def collect_slide(package: zipfile.ZipFile, slide_part: str, slide_number: int) -> dict:
    root = ET.fromstring(package.read(slide_part))
    rels = parse_relationships(package, slide_part)

    texts = []
    for shape in root.findall(".//p:sp", NS):
        text = text_from_element(shape)
        if not text:
            continue
        name, descr = c_nv_name(shape)
        box = xfrm_box(shape)
        texts.append(
            {
                "text": text,
                "normalized": normalize(text),
                "name": name,
                "description": descr,
                "box": box,
            }
        )

    pictures = []
    for pic in root.findall(".//p:pic", NS):
        name, descr = c_nv_name(pic)
        embed = ""
        blip = pic.find(".//a:blip", NS)
        if blip is not None:
            embed = blip.attrib.get(f"{{{NS['r']}}}embed", "")
        media_part = rels.get(embed, "")
        box = xfrm_box(pic)
        pic_center = center(box)
        nearest = None
        nearest_distance = None
        for text in texts:
            dist = distance(pic_center, center(text["box"]))
            if dist is None:
                continue
            if nearest_distance is None or dist < nearest_distance:
                nearest = text
                nearest_distance = dist
        pictures.append(
            {
                "name": name,
                "description": descr,
                "relationship_id": embed,
                "media_part": media_part,
                "box": box,
                "nearest_text": nearest["text"] if nearest else "",
                "nearest_text_distance_emu": nearest_distance,
            }
        )

    slide_text = " ".join(text["text"] for text in texts)
    return {
        "slide": slide_number,
        "slide_part": slide_part,
        "texts": texts,
        "pictures": pictures,
        "slide_text": slide_text,
    }


def slide_sort_key(name: str) -> int:
    match = re.search(r"slide(\d+)\.xml$", name)
    return int(match.group(1)) if match else 0


def load_slides(package: zipfile.ZipFile) -> list[dict]:
    slide_parts = sorted(
        [
            name
            for name in package.namelist()
            if name.startswith("ppt/slides/slide") and name.endswith(".xml")
        ],
        key=slide_sort_key,
    )
    return [
        collect_slide(package, slide_part, slide_sort_key(slide_part))
        for slide_part in slide_parts
    ]


def alias_patterns(alias_config: dict) -> dict[str, list[str]]:
    patterns = {}
    for icon_key, aliases in alias_config.get("aliases", {}).items():
        values = {normalize(icon_key), normalize(icon_key.replace("-", " "))}
        values.update(normalize(alias) for alias in aliases)
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
        if not pattern:
            continue
        if label_norm == pattern:
            best = max(best, 1.0)
        elif contains_phrase(label_norm, pattern):
            best = max(best, 0.88)
        elif len(label_norm) >= 8 and contains_phrase(pattern, label_norm):
            best = max(best, 0.72)
        else:
            label_words = set(label_norm.split())
            pattern_words = set(pattern.split())
            if label_words and pattern_words:
                overlap = len(label_words & pattern_words) / len(pattern_words)
                if overlap >= 0.75:
                    best = max(best, 0.58)
    return best


def picture_candidates(slides: list[dict], patterns: dict[str, list[str]]) -> list[dict]:
    candidates = []
    for slide in slides:
        for index, picture in enumerate(slide["pictures"], start=1):
            label_sources = [
                picture.get("nearest_text", ""),
                picture.get("name", ""),
                picture.get("description", ""),
            ]
            for icon_key, icon_patterns in patterns.items():
                source_scores = [
                    score_alias(label_source, icon_patterns)
                    for label_source in label_sources
                    if label_source
                ]
                score = max(source_scores) if source_scores else 0.0
                if score <= 0:
                    continue

                distance_emu = picture.get("nearest_text_distance_emu")
                if distance_emu is not None and distance_emu > 0:
                    distance_inches = distance_emu / EMU_PER_INCH
                    score = max(0.0, score - min(distance_inches / 40, 0.25))

                if score < 0.45:
                    continue

                candidates.append(
                    {
                        "icon_key": icon_key,
                        "score": round(score, 4),
                        "slide": slide["slide"],
                        "picture_index": index,
                        "source_type": "image",
                        "media_part": picture.get("media_part", ""),
                        "nearest_text": picture.get("nearest_text", ""),
                        "source_text": picture.get("nearest_text", ""),
                        "picture_name": picture.get("name", ""),
                        "picture_description": picture.get("description", ""),
                        "distance_emu": distance_emu,
                    }
                )
    return candidates


def text_candidates(slides: list[dict], patterns: dict[str, list[str]]) -> list[dict]:
    candidates = []
    for slide in slides:
        text_items = slide["texts"]
        labels = []
        for index, text in enumerate(text_items, start=1):
            labels.append((index, index, text.get("text", "")))

        for span in (2, 3):
            for start in range(0, max(0, len(text_items) - span + 1)):
                parts = [text_items[start + offset].get("text", "") for offset in range(span)]
                label = " ".join(part for part in parts if part).strip()
                labels.append((start + 1, start + span, label))

        for start_index, end_index, label in labels:
            if not label:
                continue
            for icon_key, icon_patterns in patterns.items():
                score = score_alias(label, icon_patterns)
                if score < 0.72:
                    continue
                candidates.append(
                    {
                        "icon_key": icon_key,
                        "score": round(score, 4),
                        "slide": slide["slide"],
                        "text_index": start_index,
                        "text_end_index": end_index,
                        "source_type": "shape-label",
                        "media_part": "",
                        "nearest_text": label,
                        "source_text": label,
                        "picture_name": "",
                        "picture_description": "",
                        "distance_emu": None,
                    }
                )
    return candidates


def choose_best(candidates: list[dict], alias_config: dict) -> dict[str, dict]:
    best: dict[str, dict] = {}
    preferred_source_slides = alias_config.get("preferred_source_slides", {})
    for candidate in candidates:
        icon_key = candidate["icon_key"]
        current = best.get(icon_key)
        preferred_slides = set(preferred_source_slides.get(icon_key, []))
        candidate_rank = (
            candidate["score"]
            + (0.08 if candidate.get("media_part") else 0.0)
            + (0.05 if candidate.get("slide") in preferred_slides else 0.0)
        )
        current_rank = (
            current["score"]
            + (0.08 if current.get("media_part") else 0.0)
            + (0.05 if current.get("slide") in preferred_slides else 0.0)
            if current
            else -1
        )
        if current is None or candidate_rank > current_rank:
            best[icon_key] = candidate
    return best


def copy_icon_asset(package: zipfile.ZipFile, media_part: str, icon_key: str, out_dir: Path) -> str:
    if not media_part or media_part not in package.namelist():
        return ""
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(media_part).suffix.lower() or ".bin"
    out_path = out_dir / f"{slugify(icon_key)}{suffix}"
    with package.open(media_part) as source, out_path.open("wb") as target:
        shutil.copyfileobj(source, target)
    return str(out_path.relative_to(DEFAULT_SKILL_DIR))


def clean_output_dir(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_suffixes = {".bin", ".emf", ".jpeg", ".jpg", ".png", ".svg"}
    for path in out_dir.iterdir():
        if path.is_file() and path.suffix.lower() in generated_suffixes:
            path.unlink()


def build_icon_map(
    package: zipfile.ZipFile,
    best: dict[str, dict],
    alias_config: dict,
    out_dir: Path,
) -> dict:
    icon_map: dict[str, object] = {
        "_metadata": {
            "source_pptx": str((DEFAULT_SKILL_DIR / "assets" / "OCI_Icons.pptx").relative_to(DEFAULT_SKILL_DIR)),
            "asset_dir": str(out_dir.relative_to(DEFAULT_SKILL_DIR)),
            "required_keys": alias_config.get("required_keys", []),
            "missing_required": [],
            "missing_required_assets": [],
            "shape_only_required": [],
            "fallbacks": alias_config.get("fallbacks", {}),
            "notes": [
                "Generated by scripts/extract_oci_icons.py.",
                "Scores are heuristic matches from nearby text, picture name, or picture description.",
                "shape-label entries found a matching label but no extractable media asset.",
                "Items in missing_required_assets need manual review, fallback icons, or a shape-copy implementation."
            ],
        }
    }

    for icon_key in sorted(best):
        candidate = best[icon_key]
        asset_path = copy_icon_asset(package, candidate.get("media_part", ""), icon_key, out_dir)
        icon_map[icon_key] = {
            "label": candidate.get("nearest_text") or candidate.get("picture_name") or icon_key,
            "aliases": alias_config.get("aliases", {}).get(icon_key, []),
            "asset_path": asset_path,
            "source_type": candidate.get("source_type", "image"),
            "source_slide": candidate.get("slide"),
            "source_media_part": candidate.get("media_part", ""),
            "source_picture_name": candidate.get("picture_name", ""),
            "confidence": candidate.get("score", 0),
            "match_source": {
                "nearest_text": candidate.get("nearest_text", ""),
                "source_text": candidate.get("source_text", ""),
                "picture_description": candidate.get("picture_description", ""),
                "distance_emu": candidate.get("distance_emu"),
            },
        }

    missing = [
        key
        for key in alias_config.get("required_keys", [])
        if key not in icon_map
    ]
    missing_assets = [
        key
        for key in alias_config.get("required_keys", [])
        if key not in icon_map or not icon_map.get(key, {}).get("asset_path")
    ]
    shape_only = [
        key
        for key in alias_config.get("required_keys", [])
        if key in icon_map
        and icon_map.get(key, {}).get("source_type") == "shape-label"
    ]
    icon_map["_metadata"]["missing_required"] = missing
    icon_map["_metadata"]["missing_required_assets"] = missing_assets
    icon_map["_metadata"]["shape_only_required"] = shape_only
    return icon_map


def build_inventory(slides: list[dict], candidates: list[dict], text_label_candidates: list[dict]) -> dict:
    return {
        "_metadata": {
            "slide_count": len(slides),
            "picture_count": sum(len(slide["pictures"]) for slide in slides),
            "text_box_count": sum(len(slide["texts"]) for slide in slides),
            "image_candidate_count": len(candidates),
            "text_label_candidate_count": len(text_label_candidates),
        },
        "slides": [
            {
                "slide": slide["slide"],
                "text_count": len(slide["texts"]),
                "picture_count": len(slide["pictures"]),
                "texts": [text["text"] for text in slide["texts"][:40]],
                "pictures": [
                    {
                        "name": picture.get("name", ""),
                        "description": picture.get("description", ""),
                        "media_part": picture.get("media_part", ""),
                        "nearest_text": picture.get("nearest_text", ""),
                        "distance_emu": picture.get("nearest_text_distance_emu"),
                    }
                    for picture in slide["pictures"]
                ],
            }
            for slide in slides
        ],
        "candidates": sorted(candidates, key=lambda item: (-item["score"], item["icon_key"])),
        "text_label_candidates": sorted(
            text_label_candidates,
            key=lambda item: (-item["score"], item["icon_key"], item["slide"]),
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract heuristic OCI icon mappings from the bundled OCI_Icons.pptx."
    )
    parser.add_argument(
        "--pptx",
        default=str(DEFAULT_SKILL_DIR / "assets" / "OCI_Icons.pptx"),
        help="Path to the OCI icon toolkit PPTX.",
    )
    parser.add_argument(
        "--aliases",
        default=str(DEFAULT_SKILL_DIR / "references" / "icon-aliases.json"),
        help="Path to icon aliases JSON.",
    )
    parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_SKILL_DIR / "assets" / "extracted-icons"),
        help="Output directory for matched icon assets.",
    )
    parser.add_argument(
        "--map",
        default=str(DEFAULT_SKILL_DIR / "references" / "icon-map.json"),
        help="Output path for icon-map JSON.",
    )
    parser.add_argument(
        "--inventory",
        default=str(DEFAULT_SKILL_DIR / "references" / "icon-inventory.json"),
        help="Output path for slide/icon inventory JSON.",
    )
    parser.add_argument(
        "--fail-on-missing",
        action="store_true",
        help="Exit non-zero if any required key is missing.",
    )
    args = parser.parse_args()

    pptx_path = Path(args.pptx)
    alias_path = Path(args.aliases)
    out_dir = Path(args.out_dir)
    map_path = Path(args.map)
    inventory_path = Path(args.inventory)

    if not pptx_path.exists():
        print(f"[ERROR] PPTX not found: {pptx_path}")
        return 1
    if not alias_path.exists():
        print(f"[ERROR] alias config not found: {alias_path}")
        return 1

    alias_config = read_json(alias_path)
    patterns = alias_patterns(alias_config)

    with zipfile.ZipFile(pptx_path) as package:
        slides = load_slides(package)
        image_candidates = picture_candidates(slides, patterns)
        text_label_candidates = text_candidates(slides, patterns)
        best = choose_best(image_candidates + text_label_candidates, alias_config)
        clean_output_dir(out_dir)
        icon_map = build_icon_map(package, best, alias_config, out_dir)

    inventory = build_inventory(slides, image_candidates, text_label_candidates)
    write_json(map_path, icon_map)
    write_json(inventory_path, inventory)

    mapped = [key for key in icon_map if not key.startswith("_")]
    missing = icon_map["_metadata"]["missing_required"]
    missing_assets = icon_map["_metadata"]["missing_required_assets"]
    print(f"[OK] wrote icon map: {map_path}")
    print(f"[OK] wrote inventory: {inventory_path}")
    print(f"[OK] mapped icons: {len(mapped)}")
    if missing:
        print(f"[WARN] missing required icons: {', '.join(missing)}")
    if missing_assets:
        print(f"[WARN] missing required image assets: {', '.join(missing_assets)}")
    if (missing or missing_assets) and args.fail_on_missing:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
