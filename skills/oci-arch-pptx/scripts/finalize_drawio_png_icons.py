#!/usr/bin/env python3
"""Finalize qlmanage-rendered draw.io PNG icons for PPTX use."""

from __future__ import annotations

import argparse
import json
import struct
import zlib
from collections import deque
from pathlib import Path
from typing import Any


DEFAULT_SKILL_DIR = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"expected object JSON: {path}")
    return data


def read_png_rgba(path: Path) -> tuple[int, int, list[list[list[int]]]]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG file: {path}")

    pos = 8
    width = height = bit_depth = color_type = None
    raw = b""
    while pos < len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        pos += 4
        chunk_type = data[pos : pos + 4]
        pos += 4
        chunk = data[pos : pos + length]
        pos += length + 4
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, comp, filt, interlace = struct.unpack(
                ">IIBBBBB", chunk
            )
            if comp != 0 or filt != 0 or interlace != 0:
                raise ValueError(f"unsupported PNG settings: {path}")
        elif chunk_type == b"IDAT":
            raw += chunk
        elif chunk_type == b"IEND":
            break

    if bit_depth != 8 or color_type not in (2, 6):
        raise ValueError(f"unsupported PNG color format: {path}")

    channels = 4 if color_type == 6 else 3
    bpp = channels
    stride = int(width) * channels
    scan = zlib.decompress(raw)
    previous = [0] * stride
    rows: list[list[list[int]]] = []
    index = 0

    for _ in range(int(height)):
        filter_type = scan[index]
        index += 1
        row = list(scan[index : index + stride])
        index += stride
        recon: list[int] = []
        for col, value in enumerate(row):
            left = recon[col - bpp] if col >= bpp else 0
            up = previous[col]
            upper_left = previous[col - bpp] if col >= bpp else 0
            if filter_type == 0:
                decoded = value
            elif filter_type == 1:
                decoded = (value + left) & 255
            elif filter_type == 2:
                decoded = (value + up) & 255
            elif filter_type == 3:
                decoded = (value + ((left + up) // 2)) & 255
            elif filter_type == 4:
                predictor = left + up - upper_left
                pa = abs(predictor - left)
                pb = abs(predictor - up)
                pc = abs(predictor - upper_left)
                predicted = left if pa <= pb and pa <= pc else up if pb <= pc else upper_left
                decoded = (value + predicted) & 255
            else:
                raise ValueError(f"unsupported PNG filter {filter_type}: {path}")
            recon.append(decoded)
        previous = recon

        pixels: list[list[int]] = []
        for col in range(0, len(recon), channels):
            if channels == 4:
                pixels.append(list(recon[col : col + 4]))
            else:
                pixels.append([recon[col], recon[col + 1], recon[col + 2], 255])
        rows.append(pixels)

    return int(width), int(height), rows


def write_png_rgba(path: Path, width: int, height: int, rows: list[list[list[int]]]) -> None:
    def chunk(chunk_type: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + chunk_type
            + payload
            + struct.pack(">I", zlib.crc32(chunk_type + payload) & 0xFFFFFFFF)
        )

    raw = bytearray()
    for row in rows:
        raw.append(0)
        for red, green, blue, alpha in row:
            raw.extend((red, green, blue, alpha))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def is_canvas_white(pixel: list[int]) -> bool:
    red, green, blue, alpha = pixel
    return alpha > 0 and red >= 245 and green >= 245 and blue >= 245


def transparentize_border_white(rows: list[list[list[int]]]) -> int:
    height = len(rows)
    width = len(rows[0]) if rows else 0
    queue: deque[tuple[int, int]] = deque()
    seen: set[tuple[int, int]] = set()

    for x in range(width):
        for y in (0, height - 1):
            if is_canvas_white(rows[y][x]):
                queue.append((x, y))
                seen.add((x, y))
    for y in range(height):
        for x in (0, width - 1):
            if (x, y) not in seen and is_canvas_white(rows[y][x]):
                queue.append((x, y))
                seen.add((x, y))

    while queue:
        x, y = queue.popleft()
        rows[y][x][3] = 0
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (
                0 <= nx < width
                and 0 <= ny < height
                and (nx, ny) not in seen
                and is_canvas_white(rows[ny][nx])
            ):
                seen.add((nx, ny))
                queue.append((nx, ny))

    return len(seen)


def finalize_icon(svg_path: Path) -> tuple[Path, int]:
    source_png = Path(str(svg_path) + ".png")
    output_png = svg_path.with_name(f"{svg_path.stem}.drawio.png")
    input_png = source_png if source_png.exists() else output_png
    if not input_png.exists():
        raise FileNotFoundError(f"rendered PNG not found for {svg_path}")

    width, height, rows = read_png_rgba(input_png)
    changed = transparentize_border_white(rows)
    write_png_rgba(output_png, width, height, rows)
    return output_png, changed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rename qlmanage SVG thumbnails to *.drawio.png and remove white canvas."
    )
    parser.add_argument(
        "--inventory",
        default=str(DEFAULT_SKILL_DIR / "references" / "drawio-icon-inventory.json"),
        help="Inventory JSON written by extract_drawio_icons.py.",
    )
    parser.add_argument(
        "--skill-dir",
        default=str(DEFAULT_SKILL_DIR),
        help="Skill directory used to resolve inventory asset paths.",
    )
    args = parser.parse_args()

    inventory = read_json(Path(args.inventory))
    skill_dir = Path(args.skill_dir)
    matches = inventory.get("matches")
    if not isinstance(matches, list):
        raise ValueError("inventory JSON has no matches list")

    finalized = 0
    transparentized = 0
    missing = []
    for match in matches:
        if not isinstance(match, dict):
            continue
        asset_path = str(match.get("asset_path") or "")
        if not asset_path.endswith(".svg"):
            continue
        svg_path = skill_dir / asset_path
        try:
            output_png, changed = finalize_icon(svg_path)
        except FileNotFoundError as exc:
            missing.append(str(exc))
            continue
        finalized += 1
        transparentized += changed
        print(f"[OK] {output_png.relative_to(skill_dir)} transparentized={changed}")

    if missing:
        for item in missing:
            print(f"[ERROR] {item}")
        return 1

    print(
        f"[OK] finalized {finalized} PNG icons; "
        f"transparentized {transparentized} border-connected white pixels"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
