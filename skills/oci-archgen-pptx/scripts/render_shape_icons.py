#!/usr/bin/env python3
import argparse
import json
import math
import posixpath
import re
import shutil
import subprocess
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
SLIDE_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"


def normalize(value: str) -> str:
    value = value.lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def contains_phrase(text: str, phrase: str) -> bool:
    return f" {phrase} " in f" {text} "


def score_label(label: str, patterns: list[str]) -> float:
    label_norm = normalize(label)
    if not label_norm:
        return 0.0
    best = 0.0
    for pattern in patterns:
        pattern_norm = normalize(pattern)
        if not pattern_norm:
            continue
        if label_norm == pattern_norm:
            best = max(best, 1.0)
        elif contains_phrase(label_norm, pattern_norm):
            best = max(best, 0.9)
        elif len(label_norm) >= 8 and contains_phrase(pattern_norm, label_norm):
            best = max(best, 0.72)
    return best


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def text_from_element(element: ET.Element) -> str:
    parts = [node.text or "" for node in element.findall(".//a:t", NS)]
    return " ".join(part.strip() for part in parts if part and part.strip()).strip()


def xfrm_values(element: ET.Element, group: bool) -> Optional[dict]:
    path = "./p:grpSpPr/a:xfrm" if group else "./p:spPr/a:xfrm"
    xfrm = element.find(path, NS)
    if xfrm is None:
        return None
    off = xfrm.find("a:off", NS)
    ext = xfrm.find("a:ext", NS)
    if off is None or ext is None:
        return None
    ch_off = xfrm.find("a:chOff", NS)
    ch_ext = xfrm.find("a:chExt", NS)
    return {
        "x": float(off.attrib.get("x", "0")),
        "y": float(off.attrib.get("y", "0")),
        "cx": float(ext.attrib.get("cx", "0")),
        "cy": float(ext.attrib.get("cy", "0")),
        "ch_x": float(ch_off.attrib.get("x", off.attrib.get("x", "0"))) if ch_off is not None else None,
        "ch_y": float(ch_off.attrib.get("y", off.attrib.get("y", "0"))) if ch_off is not None else None,
        "ch_cx": float(ch_ext.attrib.get("cx", ext.attrib.get("cx", "0"))) if ch_ext is not None else None,
        "ch_cy": float(ch_ext.attrib.get("cy", ext.attrib.get("cy", "0"))) if ch_ext is not None else None,
    }


def local_box(element: ET.Element, group: bool) -> Optional[tuple[float, float, float, float]]:
    values = xfrm_values(element, group)
    if values is None:
        return None
    return values["x"], values["y"], values["cx"], values["cy"]


def transform_box(box: tuple[float, float, float, float], transform: dict) -> tuple[float, float, float, float]:
    x, y, cx, cy = box
    scale_x = transform["cx"] / transform["ch_cx"] if transform.get("ch_cx") else 1.0
    scale_y = transform["cy"] / transform["ch_cy"] if transform.get("ch_cy") else 1.0
    abs_x = transform["x"] + (x - transform["ch_x"]) * scale_x
    abs_y = transform["y"] + (y - transform["ch_y"]) * scale_y
    return abs_x, abs_y, cx * scale_x, cy * scale_y


def direct_child_boxes(group: ET.Element) -> list[dict]:
    transform = xfrm_values(group, group=True)
    boxes = []
    if transform is None:
        return boxes
    for child in list(group):
        tag = child.tag.rsplit("}", 1)[-1]
        if tag not in {"grpSp", "sp"}:
            continue
        is_group = tag == "grpSp"
        box = local_box(child, group=is_group)
        if box is None:
            continue
        abs_box = transform_box(box, transform)
        boxes.append(
            {
                "tag": tag,
                "text": text_from_element(child),
                "box": abs_box,
                "area": abs_box[2] * abs_box[3],
            }
        )
    return boxes


def choose_icon_box(group: ET.Element) -> tuple[float, float, float, float]:
    group_box = local_box(group, group=True)
    if group_box is None:
        raise ValueError("matched group has no transform box")

    children = direct_child_boxes(group)
    no_text = [
        child
        for child in children
        if not child["text"] and child["box"][2] > 10000 and child["box"][3] > 10000
    ]
    if no_text:
        return max(no_text, key=lambda child: child["area"])["box"]
    return group_box


def alias_patterns(icon_key: str, icon_entry: dict, alias_config: dict) -> list[str]:
    patterns = {icon_key.replace("-", " "), icon_entry.get("label", "")}
    patterns.update(alias_config.get("aliases", {}).get(icon_key, []))
    if icon_key == "service-gateway":
        patterns.add("service gateway")
    return [pattern for pattern in patterns if pattern]


def find_icon_box(pptx: Path, slide_number: int, icon_key: str, icon_entry: dict, alias_config: dict) -> tuple[float, float, float, float]:
    patterns = alias_patterns(icon_key, icon_entry, alias_config)
    with zipfile.ZipFile(pptx) as package:
        root = ET.fromstring(package.read(f"ppt/slides/slide{slide_number}.xml"))

    candidates = []
    for group in root.findall("./p:cSld/p:spTree/p:grpSp", NS):
        label = text_from_element(group)
        score = score_label(label, patterns)
        if score <= 0:
            continue
        box = choose_icon_box(group)
        candidates.append((score, label, box))

    if not candidates:
        raise ValueError(f"no matching top-level group found for {icon_key} on slide {slide_number}")
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][2]


def read_slide_size(pptx: Path) -> tuple[int, int]:
    with zipfile.ZipFile(pptx) as package:
        root = ET.fromstring(package.read("ppt/presentation.xml"))
    size = root.find("p:sldSz", NS)
    if size is None:
        raise ValueError("presentation.xml missing p:sldSz")
    return int(size.attrib["cx"]), int(size.attrib["cy"])


def target_slide_relationship_id(pptx: Path, slide_number: int) -> str:
    target = f"slides/slide{slide_number}.xml"
    with zipfile.ZipFile(pptx) as package:
        root = ET.fromstring(package.read("ppt/_rels/presentation.xml.rels"))
    for rel in root.findall("rel:Relationship", NS):
        if rel.attrib.get("Type") == SLIDE_REL_TYPE and rel.attrib.get("Target") == target:
            return rel.attrib["Id"]
    raise ValueError(f"slide relationship not found for slide {slide_number}")


def reorder_presentation_xml(xml_bytes: bytes, rel_id: str) -> bytes:
    ET.register_namespace("a", NS["a"])
    ET.register_namespace("r", NS["r"])
    ET.register_namespace("p", NS["p"])
    root = ET.fromstring(xml_bytes)
    slide_list = root.find("p:sldIdLst", NS)
    if slide_list is None:
        raise ValueError("presentation.xml missing p:sldIdLst")
    slides = list(slide_list)
    target = None
    for slide in slides:
        if slide.attrib.get(f"{{{NS['r']}}}id") == rel_id:
            target = slide
            break
    if target is None:
        raise ValueError(f"presentation.xml missing slide id {rel_id}")
    slide_list[:] = [target] + [slide for slide in slides if slide is not target]
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def create_reordered_pptx(source: Path, slide_number: int, output: Path) -> None:
    rel_id = target_slide_relationship_id(source, slide_number)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as src, zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "ppt/presentation.xml":
                data = reorder_presentation_xml(data, rel_id)
            dst.writestr(item, data)


def run_checked(command: list[str]) -> None:
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode != 0:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(command)}\n{result.stdout}")


def rendered_png_path(output_dir: Path, pptx_path: Path) -> Path:
    return output_dir / f"{pptx_path.name}.png"


def render_slide_png(pptx: Path, output_dir: Path, size: int) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out = rendered_png_path(output_dir, pptx)
    if out.exists():
        out.unlink()
    run_checked(["qlmanage", "-t", "-s", str(size), "-o", str(output_dir), str(pptx)])
    if not out.exists():
        raise RuntimeError(f"QuickLook did not create expected PNG: {out}")
    return out


def sips_size(path: Path) -> tuple[int, int]:
    result = subprocess.run(
        ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
    )
    width = height = None
    for line in result.stdout.splitlines():
        if "pixelWidth:" in line:
            width = int(line.rsplit(":", 1)[1].strip())
        if "pixelHeight:" in line:
            height = int(line.rsplit(":", 1)[1].strip())
    if width is None or height is None:
        raise RuntimeError(f"could not read image size for {path}")
    return width, height


def emu_box_to_pixel_crop(
    box: tuple[float, float, float, float],
    slide_size: tuple[int, int],
    image_size: tuple[int, int],
    padding_ratio: float,
) -> tuple[int, int, int, int]:
    slide_w, slide_h = slide_size
    image_w, image_h = image_size
    x, y, cx, cy = box
    px = x / slide_w * image_w
    py = y / slide_h * image_h
    pw = cx / slide_w * image_w
    ph = cy / slide_h * image_h
    side = max(pw, ph) * (1 + padding_ratio)
    center_x = px + pw / 2
    center_y = py + ph / 2
    left = max(0, int(round(center_x - side / 2)))
    top = max(0, int(round(center_y - side / 2)))
    side_int = int(math.ceil(side))
    if left + side_int > image_w:
        left = max(0, image_w - side_int)
    if top + side_int > image_h:
        top = max(0, image_h - side_int)
    return left, top, side_int, side_int


def crop_and_resize(input_png: Path, output_png: Path, crop: tuple[int, int, int, int], size: int) -> None:
    left, top, width, height = crop
    output_png.parent.mkdir(parents=True, exist_ok=True)
    temp_crop = output_png.with_suffix(".crop.png")
    if temp_crop.exists():
        temp_crop.unlink()
    if output_png.exists():
        output_png.unlink()
    run_checked(
        [
            "sips",
            "--cropToHeightWidth",
            str(height),
            str(width),
            "--cropOffset",
            str(top),
            str(left),
            str(input_png),
            "--out",
            str(temp_crop),
        ]
    )
    run_checked(["sips", "-z", str(size), str(size), str(temp_crop), "--out", str(output_png)])
    temp_crop.unlink(missing_ok=True)


def update_icon_map(icon_map_path: Path, icon_map: dict, rendered: dict[str, dict]) -> None:
    for icon_key, data in rendered.items():
        entry = icon_map[icon_key]
        entry["asset_path"] = data["asset_path"]
        entry["source_type"] = "rendered-shape"
        entry["render_source"] = {
            "source_slide": data["source_slide"],
            "source_box_emu": data["source_box_emu"],
            "crop_px": data["crop_px"],
            "rendered_from": data["rendered_from"],
        }

    missing_required_assets = [
        key
        for key in icon_map["_metadata"].get("required_keys", [])
        if not icon_map.get(key, {}).get("asset_path")
    ]
    icon_map["_metadata"]["missing_required_assets"] = missing_required_assets
    icon_map["_metadata"]["rendered_shape_assets"] = sorted(rendered)
    notes = icon_map["_metadata"].setdefault("notes", [])
    note = "rendered-shape entries were rasterized from PowerPoint shapes via QuickLook slide rendering and crop."
    if note not in notes:
        notes.append(note)
    write_json(icon_map_path, icon_map)


def default_targets(icon_map: dict) -> list[str]:
    return [
        key
        for key in icon_map["_metadata"].get("missing_required_assets", [])
        if icon_map.get(key, {}).get("source_type") == "shape-label"
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render shape-only OCI icon entries to PNG assets by rendering source slides and cropping icon groups."
    )
    parser.add_argument("--pptx", default=str(DEFAULT_SKILL_DIR / "assets" / "OCI_Icons.pptx"))
    parser.add_argument("--map", default=str(DEFAULT_SKILL_DIR / "references" / "icon-map.json"))
    parser.add_argument("--aliases", default=str(DEFAULT_SKILL_DIR / "references" / "icon-aliases.json"))
    parser.add_argument("--out-dir", default=str(DEFAULT_SKILL_DIR / "assets" / "extracted-icons"))
    parser.add_argument("--work-dir", default=str(DEFAULT_SKILL_DIR.parent.parent / "tmp" / "shape-icon-render"))
    parser.add_argument("--render-size", type=int, default=2400)
    parser.add_argument("--icon-size", type=int, default=168)
    parser.add_argument("--padding-ratio", type=float, default=0.18)
    parser.add_argument("--target", action="append", default=[], help="Icon key to render. Defaults to missing required shape-label assets.")
    args = parser.parse_args()

    pptx = Path(args.pptx)
    icon_map_path = Path(args.map)
    alias_config = read_json(Path(args.aliases))
    icon_map = read_json(icon_map_path)
    out_dir = Path(args.out_dir)
    work_dir = Path(args.work_dir)
    slide_size = read_slide_size(pptx)

    targets = args.target or default_targets(icon_map)
    if not targets:
        print("[OK] no shape-only required icons need rendering")
        return 0

    work_dir.mkdir(parents=True, exist_ok=True)
    rendered: dict[str, dict] = {}
    slide_png_cache: dict[int, Path] = {}

    for icon_key in targets:
        entry = icon_map.get(icon_key)
        if not entry:
            print(f"[WARN] skipping unknown icon key: {icon_key}")
            continue
        slide_number = int(entry.get("source_slide") or 0)
        if not slide_number:
            print(f"[WARN] skipping {icon_key}: no source slide")
            continue

        box = find_icon_box(pptx, slide_number, icon_key, entry, alias_config)
        if slide_number not in slide_png_cache:
            temp_pptx = work_dir / f"slide-{slide_number}.pptx"
            render_dir = work_dir / f"slide-{slide_number}-render"
            shutil.rmtree(render_dir, ignore_errors=True)
            create_reordered_pptx(pptx, slide_number, temp_pptx)
            slide_png_cache[slide_number] = render_slide_png(temp_pptx, render_dir, args.render_size)

        slide_png = slide_png_cache[slide_number]
        image_size = sips_size(slide_png)
        crop = emu_box_to_pixel_crop(box, slide_size, image_size, args.padding_ratio)
        output_png = out_dir / f"{icon_key}.png"
        crop_and_resize(slide_png, output_png, crop, args.icon_size)
        rendered[icon_key] = {
            "asset_path": str(output_png.relative_to(DEFAULT_SKILL_DIR)),
            "source_slide": slide_number,
            "source_box_emu": [round(value, 2) for value in box],
            "crop_px": list(crop),
            "rendered_from": str(slide_png.relative_to(DEFAULT_SKILL_DIR.parent.parent)),
        }
        print(f"[OK] rendered {icon_key}: {output_png}")

    update_icon_map(icon_map_path, icon_map, rendered)
    print(f"[OK] updated icon map: {icon_map_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
