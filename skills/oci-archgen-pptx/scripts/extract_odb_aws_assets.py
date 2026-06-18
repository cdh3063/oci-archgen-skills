#!/usr/bin/env python3
"""Extract Oracle Database@AWS reference icons from a PowerPoint deck."""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET


DEFAULT_SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = Path.home() / "Downloads" / "odb-aws-architecture.pptx"
DEFAULT_OUTPUT = DEFAULT_SKILL_DIR / "assets" / "odb-aws"


ICON_PATTERNS = {
    "aws-cloud-corner.png": re.compile(r"^AWS Cloud corner icon$"),
    "aws-region-corner.png": re.compile(r"^AWS Region corner icon$"),
    "aws-vpc-corner.png": re.compile(r"^AZ a VPC corner icon$"),
    "aws-ec2-applications.png": re.compile(r"^AZ a EC2 applications icon$"),
    "odb-network-corner.png": re.compile(r"^AZ a ODB corner icon$"),
    "odb-subnet.png": re.compile(r"^AZ a ODB subnet icon$"),
    "aws-data-center-corner.png": re.compile(r"^AZ a data center corner icon$"),
    "oci-vcn.png": re.compile(r"^AZ a OCI VCN icon$"),
    "oci-subnet.png": re.compile(r"^AZ a OCI subnet icon$"),
    "exadata.png": re.compile(r"^AZ a Exadata 1$"),
    "odb-peering-marker.png": re.compile(r"^AZ a ODB peering icon$"),
    "transit-gateway.png": re.compile(r"^Transit Gateway icon$"),
    "oracle-database-at-aws.png": re.compile(r"^Oracle Database at AWS icon$"),
}


NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def qname(prefix: str, tag: str) -> str:
    return f"{{{NS[prefix]}}}{tag}"


def slide_numbers(zip_file: ZipFile) -> list[int]:
    numbers: list[int] = []
    for name in zip_file.namelist():
        match = re.fullmatch(r"ppt/slides/slide(\d+)\.xml", name)
        if match:
            numbers.append(int(match.group(1)))
    return sorted(numbers)


def slide_relationships(zip_file: ZipFile, slide_number: int) -> dict[str, str]:
    rel_path = f"ppt/slides/_rels/slide{slide_number}.xml.rels"
    if rel_path not in zip_file.namelist():
        return {}
    root = ET.fromstring(zip_file.read(rel_path))
    relationships: dict[str, str] = {}
    for rel in root.findall("rel:Relationship", NS):
        rel_id = rel.attrib.get("Id")
        target = rel.attrib.get("Target")
        if rel_id and target:
            relationships[rel_id] = target
    return relationships


def resolve_slide_target(target: str) -> str:
    return posixpath.normpath(posixpath.join("ppt/slides", target))


def picture_shapes(zip_file: ZipFile):
    for slide_number in slide_numbers(zip_file):
        rels = slide_relationships(zip_file, slide_number)
        root = ET.fromstring(zip_file.read(f"ppt/slides/slide{slide_number}.xml"))
        for pic in root.findall(".//p:pic", NS):
            name_node = pic.find(".//p:cNvPr", NS)
            blip = pic.find(".//a:blip", NS)
            if name_node is None or blip is None:
                continue
            rel_id = blip.attrib.get(qname("r", "embed"))
            target = rels.get(rel_id or "")
            if not target:
                continue
            yield slide_number, name_node.attrib.get("name", ""), resolve_slide_target(target)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract ODB@AWS reference PNG assets by picture shape name."
    )
    parser.add_argument("pptx", nargs="?", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not args.pptx.exists():
        raise FileNotFoundError(f"reference PPTX not found: {args.pptx}")

    args.out.mkdir(parents=True, exist_ok=True)
    found: dict[str, dict[str, object]] = {}
    missing = set(ICON_PATTERNS)

    with ZipFile(args.pptx) as zip_file:
        for slide_number, shape_name, media_path in picture_shapes(zip_file):
            for filename, pattern in ICON_PATTERNS.items():
                if filename not in missing:
                    continue
                if not pattern.fullmatch(shape_name):
                    continue
                blob = zip_file.read(media_path)
                output_path = args.out / filename
                output_path.write_bytes(blob)
                found[filename] = {
                    "shape_name": shape_name,
                    "slide": slide_number,
                    "sha1": hashlib.sha1(blob).hexdigest(),
                    "bytes": len(blob),
                }
                missing.remove(filename)

    manifest = {
        "source": str(args.pptx),
        "assets": found,
        "missing": sorted(missing),
    }
    (args.out / "asset-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    for filename in sorted(found):
        print(f"[OK] extracted {filename} from {found[filename]['shape_name']}")
    if missing:
        for filename in sorted(missing):
            print(f"[ERROR] missing source shape for {filename}")
        return 1
    print(f"[OK] wrote manifest: {args.out / 'asset-manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
