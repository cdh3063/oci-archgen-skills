#!/usr/bin/env python3
"""Generate a small editable OCI architecture PPTX deck from a model JSON file."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape


EMU_PER_INCH = 914400
SLIDE_W = 13.333333
SLIDE_H = 7.5
FIXED_ZIP_DATE = (1980, 1, 1, 0, 0, 0)

NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"

PRESENTATION_CT = (
    "application/vnd.openxmlformats-officedocument.presentationml."
    "presentation.main+xml"
)
SLIDE_CT = "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"
SLIDE_MASTER_CT = (
    "application/vnd.openxmlformats-officedocument.presentationml."
    "slideMaster+xml"
)
SLIDE_LAYOUT_CT = (
    "application/vnd.openxmlformats-officedocument.presentationml."
    "slideLayout+xml"
)
THEME_CT = "application/vnd.openxmlformats-officedocument.theme+xml"

RESOURCE_ICON_KEYS = {
    "app-server": "compute",
    "api-gateway": "api-gateway",
    "adb": "autonomous-db",
    "autonomous database": "autonomous-db",
    "autonomous-database": "autonomous-db",
    "bastion": "bastion",
    "compute": "compute",
    "container-engine-for-kubernetes": "container-engine-for-kubernetes",
    "cpe": "customer-premises-equipment-cpe",
    "customer-data-center": "customer-data-center",
    "customer-premises-equipment": "customer-premises-equipment-cpe",
    "database": "database",
    "exadata": "exadata-database-service",
    "fastconnect": "backbone",
    "firewall": "network-firewall",
    "kubernetes": "container-engine-for-kubernetes",
    "load-balancer": "load-balancer",
    "network-firewall": "network-firewall",
    "object-storage": "object-storage",
    "oke": "container-engine-for-kubernetes",
    "on-prem": "customer-data-center",
    "on-premises": "customer-data-center",
    "was": "compute",
    "web-server": "compute",
}

GATEWAY_ICON_KEYS = {
    "cpe": "customer-premises-equipment-cpe",
    "customer-premises-equipment": "customer-premises-equipment-cpe",
    "drg": "dynamic-routing-gateway",
    "dynamic-routing-gateway": "dynamic-routing-gateway",
    "fast-connect": "backbone",
    "fastconnect": "backbone",
    "internet-gateway": "internet-gateway",
    "local-peering-gateway": "dynamic-routing-gateway",
    "nat-gateway": "nat-gateway",
    "remote-peering-gateway": "remote-peering-gateway",
    "remote-peering-connection": "remote-peering-gateway",
    "rpg": "remote-peering-gateway",
    "service-gateway": "service-gateway",
}

GATEWAY_SHORT_LABELS = {
    "backbone": "FC",
    "customer-premises-equipment-cpe": "CPE",
    "dynamic-routing-gateway": "DRG",
    "internet-gateway": "IGW",
    "nat-gateway": "NAT",
    "remote-peering-gateway": "RPG",
    "service-gateway": "SGW",
}

TIER_ORDER = {
    "edge": 0,
    "dmz": 0,
    "public": 0,
    "security": 1,
    "inspection": 1,
    "firewall": 1,
    "web": 2,
    "app": 3,
    "application": 3,
    "private": 3,
    "data": 4,
    "db": 4,
    "database": 4,
    "management": 5,
}

STANDARD_ICON_SIZE = 0.48
STANDARD_ICON_LABEL_SIZE = 7.0
CONNECTOR_COLOR = "312D2A"
CONNECTOR_WIDTH_PT = 1.0
CONNECTOR_LABEL_COLOR = "312D2A"
CONNECTOR_LABEL_FILL = None
CONNECTOR_LABEL_SIZE = 7.4
DRAW_CONNECTOR_LABELS = False

EDGE_ICON_KEYS = {
    "api-gateway",
    "bastion",
    "flexible-load-balancer",
    "load-balancer",
    "waf",
}

SECURITY_ICON_KEYS = {
    "network-firewall",
}

APP_ICON_KEYS = {
    "api-service",
    "apex",
    "compute",
    "container-engine-for-kubernetes",
    "container-registry",
    "devops",
    "functions",
    "integrations",
    "private-endpoint-ip",
    "service-mesh",
    "visual-builder",
}

DATA_ICON_KEYS = {
    "adb-d",
    "adw-d",
    "analytics-and-ai-data-flow",
    "autonomous-data-warehouse-adw",
    "autonomous-db",
    "autonomous-transaction-processing-atp",
    "atp-d",
    "data-safe",
    "database",
    "database-database",
    "database-management",
    "exadata-c-c",
    "exadata-database-service",
    "goldengate",
    "mysql",
    "nosql",
    "opensearch",
    "rac",
}

OSN_ICON_KEYS = {
    "alarms",
    "audit",
    "buckets",
    "health-checks",
    "iam",
    "identity",
    "key-management",
    "key-vault",
    "logging",
    "logging-analytics",
    "monitoring",
    "object-storage",
    "observability-and-management-events",
    "operations-insights",
    "policies",
    "search",
    "service-connector-hub",
    "vault",
    "vcn-flow-logs",
}

EXTERNAL_ICON_KEYS = {
    "customer-data-center",
    "customer-premises-equipment-cpe",
    "goldengate-on-premises",
}

DEFAULT_CONTAINER_STYLES = {
    "region": {
        "fill": "F5F4F2",
        "line": "9E9892",
        "line_width": 1.0,
        "dash": None,
        "preset": "roundRect",
        "rounding_adj": 2000,
        "font_color": "312D2A",
    },
    "availability-domain": {
        "fill": "DFDCD8",
        "line": "9E9892",
        "line_width": 1.0,
        "dash": None,
        "preset": "roundRect",
        "rounding_adj": 1600,
        "font_color": "312D2A",
    },
    "fault-domain": {
        "fill": "FCFBFA",
        "line": "9E9892",
        "line_width": 1.0,
        "dash": None,
        "preset": "roundRect",
        "rounding_adj": 1400,
        "font_color": "312D2A",
    },
    "vcn": {
        "fill": None,
        "line": "AE562C",
        "line_width": 2.0,
        "dash": "dash",
        "preset": "rect",
        "font_color": "AE562C",
    },
    "subnet": {
        "fill": None,
        "line": "AE562C",
        "line_width": 1.0,
        "dash": "dash",
        "preset": "rect",
        "font_color": "AE562C",
    },
    "oracle-service-network": {
        "fill": "FCFBFA",
        "line": "9E9892",
        "line_width": 1.0,
        "dash": None,
        "preset": "rect",
        "font_color": "312D2A",
        "align": "center",
    },
}


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    w: float
    h: float

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


@dataclass
class IconRef:
    key: str
    label: str
    asset: Path | None
    source_type: str


def to_emu(value: float) -> int:
    return int(round(value * EMU_PER_INCH))


def xml_text(value: Any) -> str:
    return escape(str(value), {"\n": "&#10;"})


def xml_attr(value: Any) -> str:
    return escape(str(value), {'"': "&quot;", "'": "&apos;"})


def clean_color(value: str) -> str:
    return value.replace("#", "").upper()


def normalize_lookup(value: Any) -> str:
    text = str(value or "")
    text = (
        text.replace("&amp;nbsp;", " ")
        .replace("&nbsp;", " ")
        .replace("&", " and ")
        .lower()
    )
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def fill_xml(color: str | None) -> str:
    if not color:
        return "<a:noFill/>"
    return f'<a:solidFill><a:srgbClr val="{clean_color(color)}"/></a:solidFill>'


def line_xml(color: str | None, width_pt: float = 1.0, dash: str | None = None) -> str:
    if not color:
        return "<a:ln><a:noFill/></a:ln>"
    dash_xml = f'<a:prstDash val="{xml_attr(dash)}"/>' if dash else ""
    return (
        f'<a:ln w="{int(width_pt * 12700)}">'
        f'<a:solidFill><a:srgbClr val="{clean_color(color)}"/></a:solidFill>'
        f"{dash_xml}</a:ln>"
    )


def paragraph_xml(
    text: str,
    size_pt: float,
    color: str,
    bold: bool = False,
    align: str = "l",
) -> str:
    bold_attr = ' b="1"' if bold else ""
    size = int(size_pt * 100)
    return (
        f'<a:p><a:pPr algn="{align}"/>'
        f'<a:r><a:rPr lang="en-US" sz="{size}"{bold_attr}>'
        f'<a:solidFill><a:srgbClr val="{clean_color(color)}"/></a:solidFill>'
        '<a:latin typeface="Aptos"/><a:ea typeface="Malgun Gothic"/>'
        f'</a:rPr><a:t>{xml_text(text)}</a:t></a:r>'
        f'<a:endParaRPr lang="en-US" sz="{size}"/></a:p>'
    )


def text_body_xml(
    text: str,
    size_pt: float,
    color: str,
    bold: bool = False,
    align: str = "l",
    valign: str = "t",
    margin: float = 0.05,
) -> str:
    lines = str(text).splitlines() or [""]
    paras = "".join(paragraph_xml(line, size_pt, color, bold, align) for line in lines)
    margin_emu = to_emu(margin)
    return (
        f'<p:txBody><a:bodyPr wrap="square" anchor="{valign}" '
        f'lIns="{margin_emu}" tIns="{margin_emu}" '
        f'rIns="{margin_emu}" bIns="{margin_emu}"><a:normAutofit/></a:bodyPr>'
        f"<a:lstStyle/>{paras}</p:txBody>"
    )


def rels_xml(relationships: list[tuple[str, str, str]]) -> str:
    entries = []
    for rid, rel_type, target in relationships:
        entries.append(
            f'<Relationship Id="{xml_attr(rid)}" Type="{xml_attr(rel_type)}" '
            f'Target="{xml_attr(target)}"/>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Relationships xmlns="{NS_REL}">{"".join(entries)}</Relationships>'
    )


class SlideBuilder:
    def __init__(self, package: "PptxPackage") -> None:
        self.package = package
        self.shapes: list[str] = []
        self.relationships: list[tuple[str, str, str]] = []
        self._shape_id = 2
        self._rel_id = 1

    def _next_shape_id(self) -> int:
        value = self._shape_id
        self._shape_id += 1
        return value

    def _next_rel_id(self) -> str:
        value = f"rId{self._rel_id}"
        self._rel_id += 1
        return value

    def add_shape(
        self,
        name: str,
        box: Box,
        fill: str | None,
        line: str | None,
        line_width: float = 1.0,
        preset: str = "rect",
        dash: str | None = None,
        geom_adj: int | None = None,
    ) -> None:
        sid = self._next_shape_id()
        av_list = "<a:avLst/>"
        if geom_adj is not None:
            av_list = f'<a:avLst><a:gd name="adj" fmla="val {geom_adj}"/></a:avLst>'
        self.shapes.append(
            f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="{xml_attr(name)}"/>'
            '<p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr>'
            f'<a:xfrm><a:off x="{to_emu(box.x)}" y="{to_emu(box.y)}"/>'
            f'<a:ext cx="{to_emu(box.w)}" cy="{to_emu(box.h)}"/></a:xfrm>'
            f'<a:prstGeom prst="{preset}">{av_list}</a:prstGeom>'
            f"{fill_xml(fill)}{line_xml(line, line_width, dash)}</p:spPr></p:sp>"
        )

    def add_text(
        self,
        name: str,
        box: Box,
        text: str,
        size_pt: float = 12,
        color: str = "1F2937",
        bold: bool = False,
        align: str = "l",
        valign: str = "t",
        fill: str | None = None,
        line: str | None = None,
        margin: float = 0.05,
    ) -> None:
        sid = self._next_shape_id()
        self.shapes.append(
            f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="{xml_attr(name)}"/>'
            '<p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr><p:spPr>'
            f'<a:xfrm><a:off x="{to_emu(box.x)}" y="{to_emu(box.y)}"/>'
            f'<a:ext cx="{to_emu(box.w)}" cy="{to_emu(box.h)}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
            f"{fill_xml(fill)}{line_xml(line)}</p:spPr>"
            f"{text_body_xml(text, size_pt, color, bold, align, valign, margin)}</p:sp>"
        )

    def add_picture(self, name: str, box: Box, asset: Path) -> None:
        media_name = self.package.add_media(asset)
        rid = self._next_rel_id()
        self.relationships.append(
            (
                rid,
                "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
                f"../media/{media_name}",
            )
        )
        sid = self._next_shape_id()
        self.shapes.append(
            f'<p:pic><p:nvPicPr><p:cNvPr id="{sid}" name="{xml_attr(name)}"/>'
            '<p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr>'
            '<p:nvPr/></p:nvPicPr><p:blipFill>'
            f'<a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch>'
            '</p:blipFill><p:spPr>'
            f'<a:xfrm><a:off x="{to_emu(box.x)}" y="{to_emu(box.y)}"/>'
            f'<a:ext cx="{to_emu(box.w)}" cy="{to_emu(box.h)}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
            "</p:spPr></p:pic>"
        )

    def add_arrow(
        self,
        name: str,
        start: tuple[float, float],
        end: tuple[float, float],
        color: str = CONNECTOR_COLOR,
        width_pt: float = CONNECTOR_WIDTH_PT,
        dash: str | None = None,
        arrow: bool = True,
    ) -> None:
        sx, sy = start
        ex, ey = end
        x = min(sx, ex)
        y = min(sy, ey)
        w = max(abs(ex - sx), 0.001)
        h = max(abs(ey - sy), 0.001)
        flip_h = ' flipH="1"' if ex < sx else ""
        flip_v = ' flipV="1"' if ey < sy else ""
        dash_xml = f'<a:prstDash val="{xml_attr(dash)}"/>' if dash else ""
        arrow_xml = '<a:tailEnd type="triangle"/>' if arrow else ""
        sid = self._next_shape_id()
        self.shapes.append(
            f'<p:cxnSp><p:nvCxnSpPr><p:cNvPr id="{sid}" '
            f'name="{xml_attr(name)}"/><p:cNvCxnSpPr/><p:nvPr/>'
            '</p:nvCxnSpPr><p:spPr>'
            f'<a:xfrm{flip_h}{flip_v}><a:off x="{to_emu(x)}" y="{to_emu(y)}"/>'
            f'<a:ext cx="{to_emu(w)}" cy="{to_emu(h)}"/></a:xfrm>'
            '<a:prstGeom prst="straightConnector1"><a:avLst/></a:prstGeom>'
            f'<a:ln w="{int(width_pt * 12700)}">'
            f'<a:solidFill><a:srgbClr val="{clean_color(color)}"/></a:solidFill>'
            f"{dash_xml}{arrow_xml}</a:ln>"
            "</p:spPr></p:cxnSp>"
        )

    def xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<p:sld xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}">'
            '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/>'
            '<p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr>'
            '<a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
            '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm>'
            f'</p:grpSpPr>{"".join(self.shapes)}</p:spTree></p:cSld>'
            '<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>'
        )


class PptxPackage:
    def __init__(self) -> None:
        self.slides: list[SlideBuilder] = []
        self._media_by_path: dict[Path, str] = {}
        self._media_bytes: dict[str, bytes] = {}

    def new_slide(self) -> SlideBuilder:
        slide = SlideBuilder(self)
        self.slides.append(slide)
        return slide

    def add_media(self, asset: Path) -> str:
        resolved = asset.resolve()
        if resolved not in self._media_by_path:
            media_name = f"image{len(self._media_by_path) + 1}{resolved.suffix.lower()}"
            self._media_by_path[resolved] = media_name
            self._media_bytes[media_name] = resolved.read_bytes()
        return self._media_by_path[resolved]

    def write(self, output_path: Path, title: str) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_path, "w") as package:
            self._write_part(package, "[Content_Types].xml", self._content_types_xml())
            self._write_part(package, "_rels/.rels", self._root_rels_xml())
            self._write_part(package, "docProps/core.xml", self._core_xml(title))
            self._write_part(package, "docProps/app.xml", self._app_xml())
            self._write_part(package, "ppt/presentation.xml", self._presentation_xml())
            self._write_part(
                package,
                "ppt/_rels/presentation.xml.rels",
                self._presentation_rels_xml(),
            )
            self._write_part(package, "ppt/slideMasters/slideMaster1.xml", self._slide_master_xml())
            self._write_part(
                package,
                "ppt/slideMasters/_rels/slideMaster1.xml.rels",
                self._slide_master_rels_xml(),
            )
            self._write_part(package, "ppt/slideLayouts/slideLayout1.xml", self._slide_layout_xml())
            self._write_part(
                package,
                "ppt/slideLayouts/_rels/slideLayout1.xml.rels",
                self._slide_layout_rels_xml(),
            )
            self._write_part(package, "ppt/theme/theme1.xml", self._theme_xml())
            for index, slide in enumerate(self.slides, start=1):
                self._write_part(package, f"ppt/slides/slide{index}.xml", slide.xml())
                self._write_part(
                    package,
                    f"ppt/slides/_rels/slide{index}.xml.rels",
                    rels_xml(self._slide_relationships(slide)),
                )
            for media_name, data in sorted(self._media_bytes.items()):
                self._write_part(package, f"ppt/media/{media_name}", data)

    def _write_part(self, package: zipfile.ZipFile, name: str, data: str | bytes) -> None:
        info = zipfile.ZipInfo(name, FIXED_ZIP_DATE)
        info.compress_type = zipfile.ZIP_DEFLATED
        if isinstance(data, str):
            data = data.encode("utf-8")
        package.writestr(info, data)

    def _content_types_xml(self) -> str:
        media_defaults = ['<Default Extension="png" ContentType="image/png"/>']
        if any(Path(media_name).suffix.lower() == ".svg" for media_name in self._media_bytes):
            media_defaults.append('<Default Extension="svg" ContentType="image/svg+xml"/>')
        overrides = [
            f'<Override PartName="/ppt/presentation.xml" ContentType="{PRESENTATION_CT}"/>',
            f'<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="{SLIDE_MASTER_CT}"/>',
            f'<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="{SLIDE_LAYOUT_CT}"/>',
            f'<Override PartName="/ppt/theme/theme1.xml" ContentType="{THEME_CT}"/>',
            '<Override PartName="/docProps/core.xml" '
            'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
            '<Override PartName="/docProps/app.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
        ]
        for index in range(1, len(self.slides) + 1):
            overrides.append(
                f'<Override PartName="/ppt/slides/slide{index}.xml" '
                f'ContentType="{SLIDE_CT}"/>'
            )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" '
            'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            f'{"".join(media_defaults)}'
            f'{"".join(overrides)}</Types>'
        )

    def _root_rels_xml(self) -> str:
        return rels_xml(
            [
                (
                    "rId1",
                    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument",
                    "ppt/presentation.xml",
                ),
                (
                    "rId2",
                    "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties",
                    "docProps/core.xml",
                ),
                (
                    "rId3",
                    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties",
                    "docProps/app.xml",
                ),
            ]
        )

    def _presentation_rels_xml(self) -> str:
        rels = []
        for index in range(1, len(self.slides) + 1):
            rels.append(
                (
                    f"rId{index}",
                    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide",
                    f"slides/slide{index}.xml",
                )
            )
        rels.append(
            (
                f"rId{len(self.slides) + 1}",
                "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster",
                "slideMasters/slideMaster1.xml",
            )
        )
        return rels_xml(rels)

    def _slide_relationships(self, slide: SlideBuilder) -> list[tuple[str, str, str]]:
        relationships = list(slide.relationships)
        relationships.append(
            (
                f"rId{len(relationships) + 1}",
                "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout",
                "../slideLayouts/slideLayout1.xml",
            )
        )
        return relationships

    def _presentation_xml(self) -> str:
        slide_ids = []
        for index in range(1, len(self.slides) + 1):
            slide_ids.append(f'<p:sldId id="{255 + index}" r:id="rId{index}"/>')
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<p:presentation xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}">'
            f'<p:sldMasterIdLst><p:sldMasterId id="2147483648" '
            f'r:id="rId{len(self.slides) + 1}"/></p:sldMasterIdLst>'
            f'<p:sldIdLst>{"".join(slide_ids)}</p:sldIdLst>'
            f'<p:sldSz cx="{to_emu(SLIDE_W)}" cy="{to_emu(SLIDE_H)}" type="wide"/>'
            '<p:notesSz cx="6858000" cy="9144000"/></p:presentation>'
        )

    def _slide_master_rels_xml(self) -> str:
        return rels_xml(
            [
                (
                    "rId1",
                    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout",
                    "../slideLayouts/slideLayout1.xml",
                ),
                (
                    "rId2",
                    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme",
                    "../theme/theme1.xml",
                ),
            ]
        )

    def _slide_layout_rels_xml(self) -> str:
        return rels_xml(
            [
                (
                    "rId1",
                    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster",
                    "../slideMasters/slideMaster1.xml",
                )
            ]
        )

    def _slide_master_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<p:sldMaster xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}">'
            '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/>'
            '<p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr>'
            '<a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
            '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm>'
            '</p:grpSpPr></p:spTree></p:cSld>'
            '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" '
            'accent1="accent1" accent2="accent2" accent3="accent3" '
            'accent4="accent4" accent5="accent5" accent6="accent6" '
            'hlink="hlink" folHlink="folHlink"/>'
            '<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" '
            'r:id="rId1"/></p:sldLayoutIdLst>'
            '<p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles>'
            '</p:sldMaster>'
        )

    def _slide_layout_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<p:sldLayout xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}" '
            'type="blank" preserve="1"><p:cSld name="Blank">'
            '<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/>'
            '<p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr>'
            '<a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
            '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm>'
            '</p:grpSpPr></p:spTree></p:cSld>'
            '<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>'
        )

    def _theme_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<a:theme xmlns:a="{NS_A}" name="OCI Arch Theme">'
            '<a:themeElements><a:clrScheme name="OCI Arch">'
            '<a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>'
            '<a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>'
            '<a:dk2><a:srgbClr val="1F2937"/></a:dk2>'
            '<a:lt2><a:srgbClr val="F8FAFC"/></a:lt2>'
            '<a:accent1><a:srgbClr val="C74634"/></a:accent1>'
            '<a:accent2><a:srgbClr val="1F4E79"/></a:accent2>'
            '<a:accent3><a:srgbClr val="2E7D32"/></a:accent3>'
            '<a:accent4><a:srgbClr val="AD6800"/></a:accent4>'
            '<a:accent5><a:srgbClr val="0E7490"/></a:accent5>'
            '<a:accent6><a:srgbClr val="7C3AED"/></a:accent6>'
            '<a:hlink><a:srgbClr val="2563EB"/></a:hlink>'
            '<a:folHlink><a:srgbClr val="9333EA"/></a:folHlink>'
            '</a:clrScheme><a:fontScheme name="OCI Arch">'
            '<a:majorFont><a:latin typeface="Aptos Display"/>'
            '<a:ea typeface="Malgun Gothic"/><a:cs typeface="Arial"/></a:majorFont>'
            '<a:minorFont><a:latin typeface="Aptos"/>'
            '<a:ea typeface="Malgun Gothic"/><a:cs typeface="Arial"/></a:minorFont>'
            '</a:fontScheme><a:fmtScheme name="OCI Arch">'
            '<a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
            '<a:gradFill rotWithShape="1"><a:gsLst><a:gs pos="0">'
            '<a:schemeClr val="phClr"><a:lumMod val="110000"/>'
            '<a:satMod val="105000"/></a:schemeClr></a:gs><a:gs pos="100000">'
            '<a:schemeClr val="phClr"><a:lumMod val="105000"/>'
            '<a:satMod val="103000"/></a:schemeClr></a:gs></a:gsLst>'
            '<a:lin ang="5400000" scaled="0"/></a:gradFill>'
            '<a:gradFill rotWithShape="1"><a:gsLst><a:gs pos="0">'
            '<a:schemeClr val="phClr"><a:lumMod val="108000"/>'
            '<a:satMod val="105000"/></a:schemeClr></a:gs><a:gs pos="100000">'
            '<a:schemeClr val="phClr"><a:lumMod val="105000"/>'
            '<a:satMod val="103000"/></a:schemeClr></a:gs></a:gsLst>'
            '<a:lin ang="5400000" scaled="0"/></a:gradFill></a:fillStyleLst>'
            '<a:lnStyleLst><a:ln w="9525" cap="flat" cmpd="sng" algn="ctr">'
            '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
            '<a:prstDash val="solid"/></a:ln><a:ln w="25400" cap="flat" '
            'cmpd="sng" algn="ctr"><a:solidFill><a:schemeClr val="phClr"/>'
            '</a:solidFill><a:prstDash val="solid"/></a:ln><a:ln w="38100" '
            'cap="flat" cmpd="sng" algn="ctr"><a:solidFill><a:schemeClr '
            'val="phClr"/></a:solidFill><a:prstDash val="solid"/></a:ln>'
            '</a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/>'
            '</a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle>'
            '<a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst>'
            '<a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/>'
            '</a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
            '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst>'
            '</a:fmtScheme></a:themeElements></a:theme>'
        )

    def _core_xml(self, title: str) -> str:
        safe_title = xml_text(title)
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties '
            'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f"<dc:title>{safe_title}</dc:title><dc:creator>oci-arch-pptx</dc:creator>"
            "<cp:lastModifiedBy>oci-arch-pptx</cp:lastModifiedBy>"
            '<dcterms:created xsi:type="dcterms:W3CDTF">1980-01-01T00:00:00Z</dcterms:created>'
            '<dcterms:modified xsi:type="dcterms:W3CDTF">1980-01-01T00:00:00Z</dcterms:modified>'
            "</cp:coreProperties>"
        )

    def _app_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
            'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
            "<Application>oci-arch-pptx</Application>"
            "<PresentationFormat>On-screen Show (16:9)</PresentationFormat>"
            f"<Slides>{len(self.slides)}</Slides></Properties>"
        )


class Renderer:
    def __init__(self, skill_dir: Path) -> None:
        self.skill_dir = skill_dir
        self.icon_map = self._load_icon_map()
        self.icon_fallbacks = self.icon_map.get("_metadata", {}).get("fallbacks", {})
        self.icon_aliases = self._build_icon_aliases()
        self.container_styles = self._load_container_styles()
        self.icon_notes: set[str] = set()
        self.boxes: dict[str, Box] = {}
        self.gateway_ids_by_key: dict[str, str] = {}

    def _load_icon_map(self) -> dict[str, Any]:
        with (self.skill_dir / "references" / "icon-map.json").open(
            "r", encoding="utf-8"
        ) as handle:
            return json.load(handle)

    def _load_container_styles(self) -> dict[str, Any]:
        path = self.skill_dir / "references" / "container-style-map.json"
        if not path.exists():
            return {"styles": DEFAULT_CONTAINER_STYLES}
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _build_icon_aliases(self) -> dict[str, str]:
        aliases: dict[str, str] = {}
        for key, entry in self.icon_map.items():
            if key.startswith("_") or not isinstance(entry, dict):
                continue
            self._add_icon_alias(aliases, key, key)
            self._add_icon_alias(aliases, key.replace("-", " "), key)
            self._add_icon_name_aliases(aliases, entry.get("label"), key)
            for alias in entry.get("aliases") or []:
                self._add_icon_alias(aliases, alias, key)
            title = str(entry.get("source_drawio_title") or "")
            if title:
                self._add_icon_name_aliases(aliases, title, key)
        return aliases

    def _add_icon_name_aliases(self, aliases: dict[str, str], value: Any, key: str) -> None:
        self._add_icon_alias(aliases, value, key)
        text = str(value or "")
        parts = re.split(r"\s*-\s*(?:&amp;nbsp;|&nbsp;)?\s*", text, maxsplit=1)
        if len(parts) == 2:
            self._add_icon_alias(aliases, parts[1], key)

    def _add_icon_alias(self, aliases: dict[str, str], value: Any, key: str) -> None:
        normalized = normalize_lookup(value)
        if normalized and normalized not in aliases:
            aliases[normalized] = key

    def render(self, model: dict[str, Any], output_path: Path) -> None:
        package = PptxPackage()
        self._add_title_slide(package.new_slide(), model)
        self._add_diagram_slide(package.new_slide(), model)
        self._add_notes_slide(package.new_slide(), model)
        package.write(output_path, title=str(model.get("title") or "OCI Architecture"))

    def _add_title_slide(self, slide: SlideBuilder, model: dict[str, Any]) -> None:
        title = str(model.get("title") or "OCI Architecture")
        region = model.get("region") or {}
        region_name = region.get("name") or region.get("oci_region") or "OCI Region"
        oci_region = region.get("oci_region")
        vcn = model.get("vcn") or {}
        scope = f"{region_name}"
        if oci_region and oci_region != region_name:
            scope = f"{scope} ({oci_region})"
        vcns = self._model_vcns(model)
        if len(vcns) >= 2:
            region_labels = [self._region_display_label(self._vcn_region(item, model)) for item in vcns]
            vcn_names = [str(item.get("name") or f"VCN {index + 1}") for index, item in enumerate(vcns)]
            scope = " / ".join(dict.fromkeys(region_labels))
            if vcn_names:
                scope = f"{scope} - {' / '.join(vcn_names)}"
        if vcn.get("name") and len(vcns) < 2:
            scope = f"{scope} - {vcn['name']}"

        slide.add_shape("Background", Box(0, 0, SLIDE_W, SLIDE_H), "F8FAFC", None)
        slide.add_shape("Title rule", Box(0.62, 1.05, 0.08, 2.55), "C74634", None)
        slide.add_text(
            "Title",
            Box(0.9, 1.0, 10.9, 0.9),
            title,
            size_pt=31,
            color="111827",
            bold=True,
        )
        slide.add_text(
            "Scope",
            Box(0.92, 2.0, 10.8, 0.45),
            scope,
            size_pt=15,
            color="374151",
        )
        slide.add_text(
            "Deck shape",
            Box(0.92, 3.0, 8.4, 1.0),
            "Editable OCI architecture deck: title, diagram, assumptions and notes.",
            size_pt=13,
            color="4B5563",
        )
        summary = self._summary_lines(model)
        slide.add_text(
            "Model summary",
            Box(0.92, 5.1, 10.8, 1.2),
            "\n".join(summary),
            size_pt=11,
            color="374151",
        )
        slide.add_text(
            "Footer",
            Box(0.92, 6.85, 10.8, 0.28),
            "Generated by skills/oci-arch-pptx/scripts/generate_pptx.py",
            size_pt=8,
            color="6B7280",
        )

    def _add_diagram_slide(self, slide: SlideBuilder, model: dict[str, Any]) -> None:
        self.boxes = {}
        self.gateway_ids_by_key = {}

        if self._multi_vcn_layout_requested(model):
            self._add_multi_vcn_diagram_slide(slide, model)
            return

        title = str(model.get("title") or "OCI Architecture")
        region = model.get("region") or {}
        region_label = region.get("oci_region") or region.get("name") or "OCI Region"
        vcn = model.get("vcn") or {}
        vcn_label = str(vcn.get("name") or "VCN")
        if vcn.get("cidr"):
            vcn_label = f"{vcn_label} {vcn['cidr']}"

        slide.add_shape("Background", Box(0, 0, SLIDE_W, SLIDE_H), "FFFFFF", None)
        slide.add_text(
            "Diagram title",
            Box(0.35, 0.16, 12.1, 0.34),
            title,
            size_pt=15,
            color="111827",
            bold=True,
        )

        region_box = Box(1.15, 0.74, 11.65, 6.0)
        vcn_box = Box(2.18, 1.22, 8.95, 5.05)
        ad_labels = self._availability_domain_labels(model)

        self._draw_container(
            slide,
            "region",
            "Region boundary",
            region_box,
            f"OCI Region: {region_label}",
            Box(region_box.x + 0.18, region_box.y + 0.08, region_box.w - 0.36, 0.28),
            10.5,
            bold=True,
            align="ctr",
        )

        if ad_labels:
            ad_box = Box(region_box.x + 0.32, region_box.y + 0.5, region_box.w - 0.64, region_box.h - 0.78)
            self._draw_container(
                slide,
                "availability-domain",
                "Availability Domain boundary",
                ad_box,
                str(ad_labels[0]),
                Box(ad_box.x + 0.18, ad_box.y + 0.08, ad_box.w - 0.36, 0.28),
                10.0,
                bold=True,
                align="ctr",
            )
            vcn_box = Box(ad_box.x + 0.7, ad_box.y + 0.55, ad_box.w - 1.4, ad_box.h - 0.84)

        self._draw_container(
            slide,
            "vcn",
            "VCN boundary",
            vcn_box,
            vcn_label,
            Box(vcn_box.x + 0.14, vcn_box.y + 0.08, 5.2, 0.28),
            10.0,
            bold=True,
            align="l",
        )
        self._draw_icon_only(
            slide,
            "virtual-cloud-network",
            "VCN badge",
            Box(vcn_box.right - 0.15, vcn_box.y - 0.15, 0.3, 0.3),
        )
        osn_services = self._oracle_service_network_services(model)
        osn_box = None
        if osn_services:
            osn_box = self._draw_oracle_service_network(
                slide,
                region_box,
                vcn_box,
                osn_services,
            )

        subnet_boxes = self._draw_subnets(slide, model, vcn_box)
        self._draw_external_actors(slide, model, subnet_boxes, region_box, vcn_box)
        self._draw_gateways(slide, model, region_box, vcn_box, subnet_boxes, osn_box)
        self._draw_resources(slide, model, subnet_boxes, osn_box)
        show_flows = self._should_draw_flows(model)
        if show_flows:
            self._draw_flows(slide, model)
        else:
            self._draw_data_guard_exceptions(slide, model)
        legend = (
            "Primary flow arrows only; NSG/security policy details are listed on the notes slide."
            if show_flows
            else "Only the DataGuard DB relationship is shown; other traffic and security details are listed on the notes slide."
        )

        slide.add_text(
            "Legend",
            Box(0.35, 6.93, 12.25, 0.24),
            legend,
            size_pt=7.5,
            color="6B7280",
        )

    def _add_multi_vcn_diagram_slide(self, slide: SlideBuilder, model: dict[str, Any]) -> None:
        self.boxes = {}
        self.gateway_ids_by_key = {}

        title = str(model.get("title") or "OCI Architecture")
        vcns = self._model_vcns(model)[:2]
        same_region = self._same_region(vcns, model)

        slide.add_shape("Background", Box(0, 0, SLIDE_W, SLIDE_H), "FFFFFF", None)
        slide.add_text(
            "Diagram title",
            Box(0.35, 0.16, 12.1, 0.34),
            title,
            size_pt=15,
            color="111827",
            bold=True,
        )

        osn_services = self._oracle_service_network_services(model)
        shared_osn_box = None

        if same_region:
            if osn_services:
                region_box = Box(0.55, 0.72, 12.25, 6.02)
                vcn_boxes = [
                    Box(1.03, 1.23, 4.49, 5.02),
                    Box(5.92, 1.23, 4.49, 5.02),
                ]
            else:
                region_box = Box(0.75, 0.74, 11.95, 6.0)
                vcn_boxes = [
                    Box(1.50, 1.22, 4.45, 5.05),
                    Box(7.55, 1.22, 4.45, 5.05),
                ]
            self._draw_container(
                slide,
                "region",
                "Region boundary",
                region_box,
                f"OCI Region: {self._region_display_label(self._vcn_region(vcns[0], model))}",
                Box(region_box.x + 0.18, region_box.y + 0.08, region_box.w - 0.36, 0.28),
                10.5,
                bold=True,
                align="ctr",
            )
            layouts = [
                (vcns[0], region_box, vcn_boxes[0], "right"),
                (vcns[1], region_box, vcn_boxes[1], "left"),
            ]
            if osn_services:
                shared_osn_box = self._draw_oracle_service_network(
                    slide,
                    region_box,
                    vcn_boxes[-1],
                    osn_services,
                )
        else:
            region_boxes = [
                Box(0.75, 0.74, 5.75, 6.0),
                Box(6.83, 0.74, 5.95, 6.0),
            ]
            vcn_boxes = [
                Box(1.60, 1.22, 4.08, 5.05),
                Box(7.60, 1.22, 4.28, 5.05),
            ]
            layouts = []
            for index, vcn in enumerate(vcns):
                region_box = region_boxes[index]
                self._draw_container(
                    slide,
                    "region",
                    "Region boundary",
                    region_box,
                    f"OCI Region: {self._region_display_label(self._vcn_region(vcn, model))}",
                    Box(region_box.x + 0.18, region_box.y + 0.08, region_box.w - 0.36, 0.28),
                    10.0,
                    bold=True,
                    align="ctr",
                )
                layouts.append((vcn, region_box, vcn_boxes[index], "right" if index == 0 else "left"))

        all_subnet_boxes: dict[str, Box] = {}
        subnet_index = 1
        for vcn, region_box, vcn_box, peering_side in layouts:
            self._draw_container(
                slide,
                "vcn",
                "VCN boundary",
                vcn_box,
                self._vcn_label(vcn),
                Box(vcn_box.x + 0.14, vcn_box.y + 0.08, vcn_box.w - 0.28, 0.28),
                9.2,
                bold=True,
                align="l",
            )
            self._draw_icon_only(
                slide,
                "virtual-cloud-network",
                "VCN badge",
                Box(vcn_box.right - 0.15, vcn_box.y - 0.15, 0.3, 0.3),
            )

            vcn_model = dict(model)
            vcn_model["vcn"] = vcn
            vcn_model["resources"] = self._resources_for_vcn(model, vcn)
            osn_box = shared_osn_box
            subnet_boxes = self._draw_subnets(slide, vcn_model, vcn_box, start_index=subnet_index)
            subnet_index += len(self._ordered_subnets(vcn_model))
            all_subnet_boxes.update(subnet_boxes)
            self._draw_gateways(
                slide,
                vcn_model,
                region_box,
                vcn_box,
                subnet_boxes,
                osn_box,
                peering_side=peering_side,
            )
            self._draw_resources(slide, vcn_model, subnet_boxes, osn_box)

        self._draw_multi_vcn_internet_actor(slide, model, all_subnet_boxes)
        self._draw_peering_exceptions(slide, model)

        show_flows = self._should_draw_flows(model)
        if show_flows:
            self._draw_flows(slide, model)
            legend = "Primary flow arrows are shown; network peering is shown as a gateway connection."
        else:
            self._draw_data_guard_exceptions(slide, model)
            legend = "Only VCN peering and the DataGuard DB relationship are shown; other traffic and security details are listed on the notes slide."

        slide.add_text(
            "Legend",
            Box(0.35, 6.93, 12.25, 0.24),
            legend,
            size_pt=7.5,
            color="6B7280",
        )

    def _multi_vcn_layout_requested(self, model: dict[str, Any]) -> bool:
        return len(self._model_vcns(model)) >= 2

    def _model_vcns(self, model: dict[str, Any]) -> list[dict[str, Any]]:
        vcns = model.get("vcns")
        if isinstance(vcns, list):
            return [vcn for vcn in vcns if isinstance(vcn, dict)]
        vcn = model.get("vcn")
        if isinstance(vcn, dict) and vcn:
            return [vcn]
        return []

    def _vcn_region(self, vcn: dict[str, Any], model: dict[str, Any]) -> dict[str, Any]:
        region = vcn.get("region")
        if isinstance(region, dict):
            return region
        model_region = model.get("region")
        if isinstance(model_region, dict):
            return model_region
        return {}

    def _region_display_label(self, region: dict[str, Any]) -> str:
        return str(region.get("oci_region") or region.get("name") or "OCI Region")

    def _same_region(self, vcns: list[dict[str, Any]], model: dict[str, Any]) -> bool:
        region_keys = {
            normalize_lookup(self._region_display_label(self._vcn_region(vcn, model)))
            for vcn in vcns
            if self._region_display_label(self._vcn_region(vcn, model))
        }
        return len(region_keys) <= 1

    def _vcn_label(self, vcn: dict[str, Any]) -> str:
        label = str(vcn.get("name") or "VCN")
        if vcn.get("cidr"):
            label = f"{label} {vcn['cidr']}"
        return label

    def _resources_for_vcn(self, model: dict[str, Any], vcn: dict[str, Any]) -> list[dict[str, Any]]:
        vcn_id = str(vcn.get("id") or normalize_lookup(vcn.get("name")) or "")
        vcn_name = str(vcn.get("name") or "")
        subnet_names = {
            str(subnet.get("name") or "")
            for subnet in vcn.get("subnets") or []
            if isinstance(subnet, dict)
        }
        resource_ids = {
            str(resource_id)
            for subnet in vcn.get("subnets") or []
            if isinstance(subnet, dict)
            for resource_id in subnet.get("resources") or []
        }
        resources: list[dict[str, Any]] = []
        for resource in model.get("resources") or []:
            if not isinstance(resource, dict):
                continue
            rid = str(resource.get("id") or "")
            resource_vcn = str(resource.get("vcn") or resource.get("vcn_id") or "")
            subnet = str(resource.get("subnet") or "")
            if resource_vcn in {vcn_id, vcn_name} or rid in resource_ids or subnet in subnet_names:
                resources.append(resource)
        return resources

    def _draw_multi_vcn_internet_actor(
        self,
        slide: SlideBuilder,
        model: dict[str, Any],
        subnet_boxes: dict[str, Box],
    ) -> None:
        if not self._needs_internet_actor(model):
            return
        first_subnet = next(iter(subnet_boxes.values()), None)
        center_y = first_subnet.cy if first_subnet else 1.9
        user_box = Box(0.08, center_y - STANDARD_ICON_SIZE / 2, STANDARD_ICON_SIZE, STANDARD_ICON_SIZE)
        self._draw_icon(
            slide,
            "user",
            "Internet Users",
            user_box,
            label_width=1.12,
            label_size=STANDARD_ICON_LABEL_SIZE,
        )
        self.boxes["internet"] = user_box
        self.boxes["users"] = user_box
        self.boxes["external"] = user_box
        self.boxes["internet-users"] = user_box
        self.boxes["internet users"] = user_box

    def _add_notes_slide(self, slide: SlideBuilder, model: dict[str, Any]) -> None:
        slide.add_shape("Background", Box(0, 0, SLIDE_W, SLIDE_H), "F8FAFC", None)
        slide.add_text(
            "Notes title",
            Box(0.55, 0.35, 11.8, 0.45),
            "Assumptions, Security Notes, and Rendering Notes",
            size_pt=21,
            color="111827",
            bold=True,
        )

        assumptions = list(model.get("assumptions") or [])
        arch_notes = list(model.get("architecture_notes") or [])
        validation = model.get("validation") or {}
        deviations = list(validation.get("best_practice_deviations") or [])
        unresolved = list(validation.get("unresolved_questions") or [])

        if not assumptions:
            assumptions = ["No explicit assumptions were supplied in the model."]
        if not arch_notes:
            arch_notes = ["No additional architecture notes were supplied in the model."]

        left_text = self._section_text("Assumptions", assumptions)
        right_items = arch_notes[:]
        if deviations:
            right_items.append("Best-practice deviations: " + "; ".join(map(str, deviations)))
        if unresolved:
            right_items.append("Unresolved questions: " + "; ".join(map(str, unresolved)))
        right_text = self._section_text("Security and best-practice notes", right_items)

        render_items = sorted(self.icon_notes)
        if not render_items:
            render_items = ["All used OCI icons were loaded from extracted icon assets."]
        render_items.append("Containers, labels, arrows, and notes are editable PowerPoint objects.")
        render_items.append("OCI service icons are embedded image assets in this first renderer slice.")
        if not self._should_draw_flows(model):
            render_items.append("Only VCN peering and the DataGuard DB connection line are shown on the architecture slide for readability.")

        slide.add_shape("Assumptions box", Box(0.65, 1.1, 5.85, 3.25), "FFFFFF", "CBD5E1", 1.0)
        slide.add_text(
            "Assumptions",
            Box(0.85, 1.28, 5.45, 2.85),
            left_text,
            size_pt=10,
            color="374151",
        )
        slide.add_shape("Security box", Box(6.8, 1.1, 5.85, 3.25), "FFFFFF", "CBD5E1", 1.0)
        slide.add_text(
            "Security notes",
            Box(7.0, 1.28, 5.45, 2.85),
            right_text,
            size_pt=10,
            color="374151",
        )
        slide.add_shape("Rendering box", Box(0.65, 4.56, 12.0, 1.95), "FFFFFF", "CBD5E1", 1.0)
        slide.add_text(
            "Rendering notes",
            Box(0.85, 4.75, 11.55, 1.56),
            self._section_text("Rendering notes", render_items),
            size_pt=8.3,
            color="374151",
        )

    def _container_style(self, style_key: str) -> dict[str, Any]:
        styles = self.container_styles.get("styles", {})
        fallback = DEFAULT_CONTAINER_STYLES.get(style_key, DEFAULT_CONTAINER_STYLES["subnet"])
        style = styles.get(style_key, {})
        if not isinstance(style, dict):
            return fallback
        return {**fallback, **style}

    def _draw_container(
        self,
        slide: SlideBuilder,
        style_key: str,
        name: str,
        box: Box,
        label: str,
        label_box: Box,
        label_size: float,
        bold: bool = False,
        align: str | None = None,
    ) -> None:
        style = self._container_style(style_key)
        slide.add_shape(
            name,
            box,
            style.get("fill"),
            style.get("line"),
            float(style.get("line_width") or 1.0),
            preset=str(style.get("preset") or "rect"),
            dash=style.get("dash"),
            geom_adj=style.get("rounding_adj"),
        )
        slide.add_text(
            f"{name} label",
            label_box,
            label,
            size_pt=label_size,
            color=str(style.get("font_color") or "312D2A"),
            bold=bold,
            align=align or self._text_align(style),
        )

    def _text_align(self, style: dict[str, Any]) -> str:
        align = str(style.get("align") or "").lower()
        if align == "center":
            return "ctr"
        if align == "right":
            return "r"
        return "l"

    def _availability_domain_labels(self, model: dict[str, Any]) -> list[str]:
        raw = model.get("availability_domains")
        if raw is None:
            raw = (model.get("region") or {}).get("availability_domains")
        if raw is None:
            raw = (model.get("region") or {}).get("availability_domain")
        if raw is None:
            return []
        if isinstance(raw, str):
            values = [raw]
        elif isinstance(raw, list):
            values = [str(item.get("name") if isinstance(item, dict) else item) for item in raw]
        else:
            return []
        return [value for value in values if value]

    def _draw_subnets(
        self,
        slide: SlideBuilder,
        model: dict[str, Any],
        vcn_box: Box,
        start_index: int = 1,
    ) -> dict[str, Box]:
        subnets = self._ordered_subnets(model)
        count = max(len(subnets), 1)
        columns = self._subnet_layout_columns(model, count)
        rows = int(math.ceil(count / columns))
        top = vcn_box.y + 0.6
        gap_y = 0.2
        gap_x = 0.22
        height = (vcn_box.h - 0.85 - gap_y * (rows - 1)) / rows
        width = (vcn_box.w - 0.76 - gap_x * (columns - 1)) / columns
        left = vcn_box.x + 0.38
        boxes: dict[str, Box] = {}

        for index, subnet in enumerate(subnets):
            display_index = start_index + index
            col = index // rows
            row = index % rows
            box = Box(left + col * (width + gap_x), top + row * (height + gap_y), width, height)
            name = str(subnet.get("name") or f"Subnet {index + 1}")
            boxes[name] = box
            tier = str(subnet.get("tier") or subnet.get("type") or "").title()
            subnet_type = str(subnet.get("type") or "").title()
            cidr = str(subnet.get("cidr") or "")
            label_parts = [part for part in [name, subnet_type, tier] if part]
            label = " - ".join(label_parts)
            if cidr:
                label = f"{label} | {cidr}"
            self._draw_container(
                slide,
                "subnet",
                f"Subnet {display_index}",
                box,
                label,
                Box(box.x + 0.12, box.y + 0.08, box.w - 0.24, 0.24),
                8.0 if columns > 1 else 8.5,
                bold=True,
                align="l",
            )
            self._draw_subnet_badges(slide, box, display_index)
        return boxes

    def _subnet_layout_columns(self, model: dict[str, Any], subnet_count: int) -> int:
        layout = model.get("layout") or {}
        requested = layout.get("subnet_columns") if isinstance(layout, dict) else None
        try:
            if requested:
                return min(max(int(requested), 1), max(subnet_count, 1))
        except (TypeError, ValueError):
            pass
        if subnet_count <= 4:
            return 1
        return min(max(int(math.ceil(subnet_count / 4)), 2), 4)

    def _draw_subnet_badges(self, slide: SlideBuilder, box: Box, index: int) -> None:
        size = 0.23
        gap = 0.06
        right = box.right - 0.04
        y = box.y + 0.06
        self._draw_icon_only(
            slide,
            "route-table",
            f"Subnet {index} route table badge",
            Box(right - size * 2 - gap, y, size, size),
        )
        self._draw_icon_only(
            slide,
            "security-list",
            f"Subnet {index} security list badge",
            Box(right - size, y, size, size),
        )

    def _draw_external_actors(
        self,
        slide: SlideBuilder,
        model: dict[str, Any],
        subnet_boxes: dict[str, Box],
        region_box: Box,
        vcn_box: Box,
    ) -> None:
        if self._needs_internet_actor(model):
            first_subnet = next(iter(subnet_boxes.values()), None)
            center_y = first_subnet.cy if first_subnet else region_box.y + 1.1
            user_box = Box(0.34, center_y - STANDARD_ICON_SIZE / 2, STANDARD_ICON_SIZE, STANDARD_ICON_SIZE)
            self._draw_icon(
                slide,
                "user",
                "Internet Users",
                user_box,
                label_width=1.12,
                label_size=STANDARD_ICON_LABEL_SIZE,
            )
            self.boxes["internet"] = user_box
            self.boxes["users"] = user_box
            self.boxes["external"] = user_box

        networks = self._external_networks(model)
        if not networks:
            return

        gap = 0.68
        anchor_y = self._external_network_anchor_y(model, subnet_boxes, vcn_box)
        start_y = anchor_y - gap * (len(networks) - 1) / 2
        for index, network in enumerate(networks):
            center_y = min(max(start_y + index * gap, region_box.y + 0.95), region_box.bottom - 0.9)
            label = str(network.get("label") or network.get("type") or "On-Prem")
            icon_key = str(network.get("icon_key") or network.get("type") or "customer-data-center")
            icon_key = self._canonical_icon_key(icon_key) or icon_key
            icon_box = Box(0.34, center_y - STANDARD_ICON_SIZE / 2, STANDARD_ICON_SIZE, STANDARD_ICON_SIZE)
            self._draw_icon(
                slide,
                icon_key,
                label,
                icon_box,
                label_width=1.12,
                label_size=STANDARD_ICON_LABEL_SIZE,
            )
            network_id = str(network.get("id") or normalize_lookup(label) or f"external-{index + 1}")
            for alias in self._external_network_aliases(network, label, network_id):
                self.boxes[alias] = icon_box

    def _needs_internet_actor(self, model: dict[str, Any]) -> bool:
        if self._has_gateway_type(model, {"internet-gateway"}):
            return True
        for flow in list(model.get("flows") or []) + list(model.get("connections") or []):
            if not isinstance(flow, dict):
                continue
            source = normalize_lookup(flow.get("from") or flow.get("source"))
            target = normalize_lookup(flow.get("to") or flow.get("target"))
            if source in {"internet", "users", "external"} or target in {"internet", "users", "external"}:
                return True
        return False

    def _external_network_anchor_y(
        self,
        model: dict[str, Any],
        subnet_boxes: dict[str, Box],
        vcn_box: Box,
    ) -> float:
        if self._has_gateway_type(model, {"drg", "dynamic-routing-gateway"}):
            return (
                self._gateway_y("dynamic-routing-gateway", "drg", subnet_boxes, vcn_box)
                + STANDARD_ICON_SIZE / 2
            )
        return vcn_box.cy

    def _external_networks(self, model: dict[str, Any]) -> list[dict[str, Any]]:
        networks: list[dict[str, Any]] = []
        seen: set[str] = set()

        raw_networks = model.get("external_networks")
        if isinstance(raw_networks, dict):
            raw_networks = [raw_networks]
        for item in raw_networks or []:
            self._append_external_network(networks, seen, item)

        on_premises = model.get("on_premises")
        if on_premises is True:
            self._append_external_network(networks, seen, {"id": "on-prem", "label": "On-Prem", "type": "customer-data-center"})
        elif isinstance(on_premises, dict):
            self._append_external_network(networks, seen, on_premises)
        elif isinstance(on_premises, list):
            for item in on_premises:
                self._append_external_network(networks, seen, item)

        for resource in model.get("resources") or []:
            if isinstance(resource, dict) and self._is_external_resource(resource):
                self._append_external_network(networks, seen, resource)

        for flow in list(model.get("flows") or []) + list(model.get("connections") or []):
            if not isinstance(flow, dict):
                continue
            for endpoint in (flow.get("from") or flow.get("source"), flow.get("to") or flow.get("target")):
                if self._is_external_endpoint(endpoint):
                    self._append_external_network(
                        networks,
                        seen,
                        {"id": "on-prem", "label": "On-Prem", "type": "customer-data-center"},
                    )
        return networks

    def _append_external_network(
        self,
        networks: list[dict[str, Any]],
        seen: set[str],
        item: Any,
    ) -> None:
        if isinstance(item, str):
            item = {"id": item, "label": item, "type": "customer-data-center"}
        if not isinstance(item, dict):
            return
        raw = item.get("icon_key") or item.get("type") or item.get("label") or "customer-data-center"
        icon_key = self._canonical_icon_key(raw) or self._canonical_icon_key("customer-data-center") or "customer-data-center"
        label = str(item.get("label") or self._icon_label(icon_key) or raw or "On-Prem")
        network_id = str(item.get("id") or normalize_lookup(label) or icon_key)
        normalized = normalize_lookup(network_id or label)
        if normalized in seen:
            return
        seen.add(normalized)
        network = dict(item)
        network["id"] = network_id
        network["type"] = str(item.get("type") or icon_key)
        network["icon_key"] = icon_key
        network["label"] = label
        networks.append(network)

    def _external_network_aliases(
        self,
        network: dict[str, Any],
        label: str,
        network_id: str,
    ) -> set[str]:
        aliases = {
            network_id,
            network_id.lower(),
            normalize_lookup(network_id),
            normalize_lookup(label),
        }
        for value in (
            network.get("type"),
            network.get("icon_key"),
            "on-prem",
            "onprem",
            "on-premises",
            "customer-dc",
            "customer-data-center",
        ):
            normalized = normalize_lookup(value)
            if normalized:
                aliases.add(normalized)
            raw = str(value or "")
            if raw:
                aliases.add(raw)
                aliases.add(raw.lower())
        return {alias for alias in aliases if alias}

    def _draw_oracle_service_network(
        self,
        slide: SlideBuilder,
        region_box: Box,
        vcn_box: Box,
        services: list[dict[str, Any]],
    ) -> Box:
        x = vcn_box.right + 0.52
        box = Box(x, vcn_box.y, region_box.right - x - 0.3, vcn_box.h)
        self._draw_container(
            slide,
            "oracle-service-network",
            "Oracle Service Network boundary",
            box,
            "OSN",
            Box(box.x + 0.06, box.y + 0.12, box.w - 0.12, 0.24),
            8.0,
            bold=True,
            align="ctr",
        )

        icon_size = STANDARD_ICON_SIZE
        first_center_y = box.y + 1.24
        last_center_y = box.bottom - 1.35
        step = (last_center_y - first_center_y) / max(len(services) - 1, 1)
        for index, service in enumerate(services):
            icon_key = str(service.get("icon_key") or service.get("type") or "")
            label = str(service.get("label") or icon_key or "Service")
            center_y = first_center_y + index * step
            icon_box = Box(box.cx - icon_size / 2, center_y - icon_size / 2, icon_size, icon_size)
            self._draw_icon(
                slide,
                icon_key,
                label,
                icon_box,
                label_width=box.w - 0.08,
                label_size=STANDARD_ICON_LABEL_SIZE,
            )
            service_id = str(service.get("id") or "")
            if service_id:
                self.boxes[service_id] = icon_box
            self.boxes[icon_key] = icon_box
            self.boxes[normalize_lookup(label)] = icon_box

        self.boxes["oracle-service-network"] = box
        self.boxes["osn"] = box
        return box

    def _oracle_service_network_services(self, model: dict[str, Any]) -> list[dict[str, Any]]:
        explicit_osn = "oracle_service_network" in model
        explicit_public = "public_services" in model
        services: list[dict[str, Any]] = []
        seen: set[str] = set()

        osn_config = model.get("oracle_service_network")
        if osn_config is False or osn_config is None and explicit_osn:
            return []
        if isinstance(osn_config, dict):
            if osn_config.get("enabled") is False:
                return []
            for item in osn_config.get("services") or []:
                self._append_osn_service(services, seen, item)
        elif isinstance(osn_config, list):
            for item in osn_config:
                self._append_osn_service(services, seen, item)

        for item in model.get("public_services") or []:
            self._append_osn_service(services, seen, item)

        subnet_resource_ids = self._resource_ids_declared_in_subnets(model)
        for resource in model.get("resources") or []:
            rid = str(resource.get("id") or "") if isinstance(resource, dict) else ""
            if (
                isinstance(resource, dict)
                and rid not in subnet_resource_ids
                and self._is_osn_resource(resource)
            ):
                self._append_osn_service(services, seen, resource)

        if services:
            return services
        return services

    def _append_osn_service(
        self,
        services: list[dict[str, Any]],
        seen: set[str],
        item: Any,
    ) -> None:
        service = self._normalize_osn_service(item)
        if not service:
            return
        key = str(service.get("id") or service.get("icon_key") or service.get("type") or service.get("label"))
        normalized = normalize_lookup(key)
        if normalized in seen:
            return
        seen.add(normalized)
        services.append(service)

    def _normalize_osn_service(self, item: Any) -> dict[str, Any]:
        if isinstance(item, str):
            icon_key = self._canonical_icon_key(item) or item
            label = self._icon_label(icon_key) or item
            return {"id": icon_key, "type": icon_key, "icon_key": icon_key, "label": label}
        if not isinstance(item, dict):
            return {}
        raw = item.get("icon_key") or item.get("type") or item.get("label") or item.get("id")
        icon_key = self._canonical_icon_key(raw) or str(raw or "object-storage")
        label = str(item.get("label") or self._icon_label(icon_key) or raw or icon_key)
        result = dict(item)
        result["type"] = icon_key
        result["icon_key"] = icon_key
        result["label"] = label
        result["id"] = str(item.get("id") or icon_key)
        return result

    def _icon_label(self, icon_key: str) -> str:
        entry = self.icon_map.get(icon_key)
        if isinstance(entry, dict):
            return str(entry.get("label") or "")
        return ""

    def _has_service_gateway(self, model: dict[str, Any]) -> bool:
        return self._has_gateway_type(model, {"service-gateway"})

    def _has_gateway_type(self, model: dict[str, Any], keys: set[str]) -> bool:
        for gateway in self._iter_model_gateways(model):
            if not isinstance(gateway, dict):
                continue
            gateway_type = str(gateway.get("type") or "").lower()
            mapped = GATEWAY_ICON_KEYS.get(gateway_type, gateway_type)
            key = self._canonical_icon_key(mapped) or mapped
            if key in keys or gateway_type in keys:
                return True
            label = normalize_lookup(gateway.get("label"))
            if any(label == normalize_lookup(item) for item in keys):
                return True
        return False

    def _iter_model_gateways(self, model: dict[str, Any]) -> list[Any]:
        gateways: list[Any] = []
        vcns = self._model_vcns(model)
        if vcns:
            for vcn in vcns:
                gateways.extend((vcn.get("gateways") or []))
            return gateways
        gateways.extend((model.get("vcn") or {}).get("gateways") or [])
        return gateways

    def _resource_ids_declared_in_subnets(self, model: dict[str, Any]) -> set[str]:
        ids: set[str] = set()
        for subnet in (model.get("vcn") or {}).get("subnets") or []:
            if not isinstance(subnet, dict):
                continue
            for resource_id in subnet.get("resources") or []:
                value = str(resource_id or "")
                if value:
                    ids.add(value)
        return ids

    def _is_osn_resource(self, resource: dict[str, Any]) -> bool:
        if not isinstance(resource, dict):
            return False
        for field in ("placement", "location", "network_scope"):
            if self._is_osn_value(resource.get(field)):
                return True
        subnet = resource.get("subnet")
        if subnet:
            return self._is_osn_value(subnet)
        return self._resource_placement(resource) == "osn"

    def _is_external_resource(self, resource: dict[str, Any]) -> bool:
        if not isinstance(resource, dict):
            return False
        for field in ("placement", "location", "network_scope", "subnet"):
            if self._is_external_value(resource.get(field)):
                return True
        return self._resource_placement(resource) == "external"

    def _is_osn_value(self, value: Any) -> bool:
        normalized = normalize_lookup(value)
        return normalized in {
            "osn",
            "oracle service network",
            "oracle services network",
            "oracle public services",
            "public services",
        }

    def _is_external_value(self, value: Any) -> bool:
        normalized = normalize_lookup(value)
        return normalized in {
            "external",
            "on prem",
            "on premise",
            "on premises",
            "onprem",
            "customer data center",
            "customer dc",
            "cpe",
        }

    def _is_external_endpoint(self, value: Any) -> bool:
        return self._is_external_value(value)

    def _resource_placement(self, resource: dict[str, Any]) -> str:
        explicit = normalize_lookup(resource.get("placement") or resource.get("tier"))
        if explicit in {"edge", "dmz", "public"}:
            return "edge"
        if explicit in {"security", "inspection", "firewall"}:
            return "security"
        if explicit in {"app", "application", "private", "workload"}:
            return "app"
        if explicit in {"data", "db", "database"}:
            return "data"
        if explicit in {"management", "mgmt"}:
            return "management"
        if self._is_osn_value(explicit):
            return "osn"
        if self._is_external_value(explicit):
            return "external"

        icon_key = self._resource_icon_key(resource)
        if icon_key in OSN_ICON_KEYS:
            return "osn"
        if icon_key in EXTERNAL_ICON_KEYS:
            return "external"
        if icon_key in SECURITY_ICON_KEYS:
            return "security"
        if icon_key in EDGE_ICON_KEYS:
            return "edge"
        if icon_key in DATA_ICON_KEYS:
            return "data"
        if icon_key in APP_ICON_KEYS:
            return "app"

        text = normalize_lookup(
            " ".join(
                str(resource.get(field) or "")
                for field in ("type", "label", "icon_key", "notes")
            )
        )
        if any(
            term in text
            for term in (
                "firewall",
            )
        ):
            return "security"
        if any(
            term in text
            for term in (
                "api gateway",
                "bastion",
                "load balancer",
                "web application firewall",
                "waf",
            )
        ):
            return "edge"
        if any(
            term in text
            for term in (
                "autonomous",
                "data flow",
                "data safe",
                "database",
                "db",
                "exadata",
                "mysql",
                "nosql",
                "opensearch",
            )
        ):
            return "data"
        if any(
            term in text
            for term in (
                "audit",
                "bucket",
                "iam",
                "logging",
                "monitoring",
                "object storage",
                "service connector",
                "vault",
            )
        ):
            return "osn"
        if any(
            term in text
            for term in (
                "customer data center",
                "customer premises",
                "on prem",
                "on premises",
            )
        ):
            return "external"
        if any(
            term in text
            for term in (
                "api service",
                "app",
                "compute",
                "container",
                "function",
                "kubernetes",
                "oke",
                "service mesh",
                "was",
                "web",
            )
        ):
            return "app"
        return "app"

    def _inferred_resource_subnet(
        self,
        resource: dict[str, Any],
        subnet_boxes: dict[str, Box],
    ) -> str:
        explicit_subnet = str(resource.get("subnet") or "")
        if explicit_subnet in subnet_boxes:
            return explicit_subnet

        placement = self._resource_placement(resource)
        if placement == "osn":
            return ""
        if placement == "edge":
            return self._first_subnet_name_matching(
                subnet_boxes, ["public", "edge", "dmz", "ingress"]
            )
        if placement == "security":
            return self._first_subnet_name_matching(
                subnet_boxes, ["security", "inspection", "firewall"]
            ) or self._first_subnet_name_matching(
                subnet_boxes, ["public", "edge", "dmz", "ingress"]
            )
        if placement == "data":
            return self._first_subnet_name_matching(
                subnet_boxes, ["data", "database", "db", "storage"]
            )
        if placement == "management":
            return self._first_subnet_name_matching(subnet_boxes, ["management", "mgmt"])
        return self._first_subnet_name_matching(
            subnet_boxes, ["app", "application", "private", "workload"]
        ) or next(iter(subnet_boxes.keys()), "")

    def _first_subnet_name_matching(
        self,
        subnet_boxes: dict[str, Box],
        terms: list[str],
    ) -> str:
        normalized_terms = [normalize_lookup(term) for term in terms]
        for term in normalized_terms:
            for name in subnet_boxes:
                if term and term in normalize_lookup(name):
                    return name
        return ""

    def _draw_gateways(
        self,
        slide: SlideBuilder,
        model: dict[str, Any],
        region_box: Box,
        vcn_box: Box,
        subnet_boxes: dict[str, Box],
        osn_box: Box | None,
        peering_side: str | None = None,
    ) -> None:
        gateways = list((model.get("vcn") or {}).get("gateways") or [])
        left_ys: list[float] = []
        right_ys: list[float] = []
        for gateway in gateways:
            gateway_type = str(gateway.get("type") or "").lower()
            mapped_key = GATEWAY_ICON_KEYS.get(gateway_type, gateway_type)
            key = self._canonical_icon_key(mapped_key) or mapped_key
            short_label = self._gateway_short_label(key, gateway_type, gateway)
            if key == "service-gateway" and osn_box is not None:
                if peering_side == "right":
                    x = vcn_box.x + 0.10
                    preferred_y = self._gateway_y(key, gateway_type, subnet_boxes, vcn_box)
                    occupied = left_ys
                else:
                    x = osn_box.x - STANDARD_ICON_SIZE
                    preferred_y = self._gateway_y(key, gateway_type, subnet_boxes, vcn_box)
                    occupied = right_ys
                y = self._avoid_gateway_overlap(
                    preferred_y,
                    occupied,
                    region_box.y + 0.72,
                    region_box.bottom - 0.92,
                )
                occupied.append(y)
            elif gateway_type in {"local-peering-gateway", "lpg", "remote-peering-gateway", "remote-peering-connection", "rpg"}:
                side = peering_side or str(gateway.get("side") or "left").lower()
                x = vcn_box.right + 0.24 if side == "right" else vcn_box.x - 0.72
                occupied = right_ys if side == "right" else left_ys
                y = self._gateway_y(key, gateway_type, subnet_boxes, vcn_box)
                occupied.append(y)
            elif key == "service-gateway":
                x = vcn_box.right + 0.32
                y = self._avoid_gateway_overlap(
                    self._gateway_y(key, gateway_type, subnet_boxes, vcn_box),
                    right_ys,
                    region_box.y + 0.72,
                    region_box.bottom - 0.92,
                )
                right_ys.append(y)
            else:
                x = vcn_box.x - 0.78
                y = self._avoid_gateway_overlap(
                    self._gateway_y(key, gateway_type, subnet_boxes, vcn_box),
                    left_ys,
                    region_box.y + 0.72,
                    region_box.bottom - 0.92,
                )
                left_ys.append(y)
            icon_box = Box(x, y, STANDARD_ICON_SIZE, STANDARD_ICON_SIZE)
            label_width = 0.62 if key == "service-gateway" else 1.05
            self._draw_icon(
                slide,
                key,
                short_label,
                icon_box,
                label_width=label_width,
                label_size=STANDARD_ICON_LABEL_SIZE,
            )

            gateway_id = str(gateway.get("id") or key)
            self.boxes[gateway_id] = icon_box
            self.boxes[key] = icon_box
            self.boxes[gateway_type] = icon_box
            self.boxes[normalize_lookup(gateway_type)] = icon_box
            self.boxes[short_label.lower()] = icon_box
            self.boxes[normalize_lookup(short_label)] = icon_box
            self.gateway_ids_by_key[key] = gateway_id

            full_label = str(gateway.get("label") or "")
            if full_label and full_label != short_label:
                self.icon_notes.add(f"{short_label}: {full_label}")

    def _gateway_short_label(
        self,
        key: str,
        gateway_type: str,
        gateway: dict[str, Any],
    ) -> str:
        if gateway_type in {"local-peering-gateway", "lpg"}:
            return "LPG"
        if gateway_type in {"remote-peering-gateway", "remote-peering-connection", "rpg"}:
            return "RPG"
        return GATEWAY_SHORT_LABELS.get(key, str(gateway.get("label") or key))

    def _draw_resources(
        self,
        slide: SlideBuilder,
        model: dict[str, Any],
        subnet_boxes: dict[str, Box],
        osn_box: Box | None,
    ) -> None:
        resources = list(model.get("resources") or [])
        by_id = {str(resource.get("id")): resource for resource in resources if resource.get("id")}
        resources_by_subnet: dict[str, list[dict[str, Any]]] = {name: [] for name in subnet_boxes}
        assigned_ids: set[str] = set()

        for subnet in self._ordered_subnets(model):
            subnet_name = str(subnet.get("name") or "")
            seen_ids: set[str] = set()
            for resource_id in subnet.get("resources") or []:
                resource = by_id.get(str(resource_id))
                if resource:
                    if self._is_osn_resource(resource) or self._is_external_resource(resource):
                        continue
                    resources_by_subnet.setdefault(subnet_name, []).append(resource)
                    seen_ids.add(str(resource_id))
                    assigned_ids.add(str(resource_id))
            for resource in resources:
                if self._is_osn_resource(resource) or self._is_external_resource(resource):
                    continue
                if str(resource.get("subnet") or "") == subnet_name:
                    rid = str(resource.get("id") or "")
                    if rid not in seen_ids:
                        resources_by_subnet.setdefault(subnet_name, []).append(resource)
                        assigned_ids.add(rid)

        for resource in resources:
            rid = str(resource.get("id") or "")
            if (
                rid in assigned_ids
                or self._is_osn_resource(resource)
                or self._is_external_resource(resource)
            ):
                continue
            subnet_name = self._inferred_resource_subnet(resource, subnet_boxes)
            if subnet_name:
                resources_by_subnet.setdefault(subnet_name, []).append(resource)
                assigned_ids.add(rid)

        for subnet_name, subnet_box in subnet_boxes.items():
            expanded = self._expand_resources(resources_by_subnet.get(subnet_name, []))
            if not expanded:
                continue
            content = Box(
                subnet_box.x + 0.32,
                subnet_box.y + 0.45,
                subnet_box.w - 0.64,
                max(subnet_box.h - 0.53, 0.45),
            )
            columns = self._resource_grid_columns(len(expanded), content)
            rows = int(math.ceil(len(expanded) / columns))
            cell_w = content.w / columns
            cell_h = content.h / rows
            resource_boxes_by_id: dict[str, list[Box]] = {}

            for index, instance in enumerate(expanded):
                col = index % columns
                row = index // columns
                label = str(instance["label"])
                key = self._resource_icon_key(instance["resource"])
                icon_size = self._resource_icon_size(key, cell_h)
                x = content.x + col * cell_w + (cell_w - icon_size) / 2
                if rows == 1:
                    y = subnet_box.cy - icon_size / 2
                else:
                    y = content.y + row * cell_h + max((cell_h - icon_size - 0.24) / 2, 0.0)
                icon_box = Box(x, y, icon_size, icon_size)
                self._draw_icon(
                    slide,
                    key,
                    label,
                    icon_box,
                    max(cell_w, 0.85),
                    STANDARD_ICON_LABEL_SIZE,
                )

                rid = str(instance["resource"].get("id") or "")
                if rid:
                    resource_boxes_by_id.setdefault(rid, []).append(icon_box)
                    self.boxes[f"{rid}:{instance['index']}"] = icon_box

            for rid, boxes in resource_boxes_by_id.items():
                self.boxes[rid] = self._union_boxes(boxes)

    def _resource_grid_columns(self, item_count: int, content: Box) -> int:
        max_by_width = max(1, int(content.w / 0.78))
        columns = min(item_count, max_by_width, 5)
        while columns > 1:
            rows = int(math.ceil(item_count / columns))
            if rows == 1 or content.h / rows >= 0.62:
                break
            columns -= 1
        return max(columns, 1)

    def _draw_flows(self, slide: SlideBuilder, model: dict[str, Any]) -> None:
        connections = list(model.get("connections") or [])
        flows = list(model.get("flows") or [])
        if not flows:
            flows = self._synthetic_flows(model)
        flows = connections + flows

        drawn: set[tuple[str, str, str]] = set()
        drawn_labels: set[tuple[str, str, str]] = set()
        horizontal_route_counts: dict[int, int] = {}
        source_label_counts, target_label_counts = self._flow_label_counts(flows)
        for flow in flows:
            if isinstance(flow, dict) and self._is_peering_connection(flow):
                continue
            source_id_raw = str(flow.get("from") or flow.get("source") or "")
            target_id_raw = str(flow.get("to") or flow.get("target") or "")
            source = self._box_for_endpoint(source_id_raw)
            target = self._box_for_endpoint(target_id_raw)
            flow_type = normalize_lookup(flow.get("type") or flow.get("kind"))
            label = str(flow.get("label") or flow.get("type") or "")
            if not source or not target:
                continue

            from_id = source_id_raw.lower()
            to_id = target_id_raw.lower()
            label_key = self._flow_label_group_key(
                from_id,
                to_id,
                label,
                source_label_counts,
                target_label_counts,
            )
            display_label = label
            if label and label_key in drawn_labels:
                display_label = ""
            elif label:
                drawn_labels.add(label_key)
            arrow = bool(flow.get("arrow", True))
            if flow_type in {
                "connection",
                "dedicated connection",
                "fast connect",
                "fastconnect",
                "ipsec vpn",
                "private circuit",
                "vpn",
            }:
                arrow = False
            dash = "dash" if "admin" in label.lower() or "ssh" in label.lower() or flow_type == "vpn" else None
            if from_id in {"internet", "users", "external"} and "internet-gateway" in self.boxes:
                igw = self.boxes["internet-gateway"]
                self._draw_arrow_once(
                    slide,
                    drawn,
                    horizontal_route_counts,
                    "internet",
                    "internet-gateway",
                    "",
                    source,
                    igw,
                )
                self._draw_arrow_once(
                    slide,
                    drawn,
                    horizontal_route_counts,
                    "internet-gateway",
                    to_id,
                    display_label,
                    igw,
                    target,
                    arrow=arrow,
                )
                continue

            osn_box = self.boxes.get("osn")
            if (
                osn_box is not None
                and "service-gateway" in self.boxes
                and to_id not in {"service-gateway", "sgw"}
                and self._box_inside(target, osn_box)
            ):
                sgw = self.boxes["service-gateway"]
                self._draw_arrow_once(
                    slide,
                    drawn,
                    horizontal_route_counts,
                    from_id,
                    "service-gateway",
                    display_label,
                    source,
                    sgw,
                    dash,
                    arrow,
                )
                self._draw_arrow_once(
                    slide,
                    drawn,
                    horizontal_route_counts,
                    "service-gateway",
                    to_id,
                    "",
                    sgw,
                    target,
                    dash,
                    arrow,
                )
                continue

            self._draw_arrow_once(
                slide,
                drawn,
                horizontal_route_counts,
                from_id,
                to_id,
                display_label,
                source,
                target,
                dash,
                arrow,
            )

    def _should_draw_flows(self, model: dict[str, Any]) -> bool:
        layout = model.get("layout") or {}
        if not isinstance(layout, dict):
            return True
        for key in ("show_flows", "show_connections", "show_connection_lines"):
            if key in layout:
                return bool(layout[key])
        return True

    def _draw_peering_exceptions(self, slide: SlideBuilder, model: dict[str, Any]) -> None:
        drawn: set[tuple[str, str]] = set()
        for connection in list(model.get("connections") or []):
            if not isinstance(connection, dict) or not self._is_peering_connection(connection):
                continue
            source_id = str(connection.get("from") or connection.get("source") or "")
            target_id = str(connection.get("to") or connection.get("target") or "")
            source = self._box_for_endpoint(source_id)
            target = self._box_for_endpoint(target_id)
            if not source or not target:
                continue
            key = tuple(sorted((normalize_lookup(source_id), normalize_lookup(target_id))))
            if key in drawn:
                continue
            drawn.add(key)
            start, end = self._edge_points(source, target)
            slide.add_arrow(
                f"Peering connection {source_id} to {target_id}",
                start,
                end,
                arrow=False,
            )

    def _is_peering_connection(self, connection: dict[str, Any]) -> bool:
        values = [
            connection.get("type"),
            connection.get("kind"),
            connection.get("label"),
            connection.get("id"),
        ]
        for value in values:
            normalized = normalize_lookup(value)
            compact = normalized.replace(" ", "").replace("-", "")
            if compact in {
                "localpeering",
                "localpeeringgateway",
                "lpg",
                "remotepeering",
                "remotepeeringgateway",
                "remotepeeringconnection",
                "rpg",
            }:
                return True
            if "local peering" in normalized or "remote peering" in normalized:
                return True
        return False

    def _draw_data_guard_exceptions(self, slide: SlideBuilder, model: dict[str, Any]) -> None:
        resources = self._resources_by_id(model)
        for flow in list(model.get("connections") or []) + list(model.get("flows") or []):
            if not isinstance(flow, dict):
                continue
            label = str(flow.get("label") or flow.get("type") or "")
            if normalize_lookup(label).replace(" ", "") != "dataguard":
                continue
            source_id = str(flow.get("from") or flow.get("source") or "")
            target_id = str(flow.get("to") or flow.get("target") or "")
            if not (
                self._is_database_resource(resources.get(normalize_lookup(source_id)))
                and self._is_database_resource(resources.get(normalize_lookup(target_id)))
            ):
                continue
            source = self._box_for_endpoint(source_id)
            target = self._box_for_endpoint(target_id)
            if not source or not target:
                continue
            start, end = self._edge_points(source, target)
            display_label = "DataGuard"
            slide.add_arrow(
                f"DataGuard connection {source_id} to {target_id}",
                start,
                end,
                arrow=False,
            )
            slide.add_text(
                f"DataGuard label {source_id} to {target_id}",
                self._flow_label_box(start, end, display_label),
                display_label,
                size_pt=CONNECTOR_LABEL_SIZE,
                color=CONNECTOR_LABEL_COLOR,
                bold=True,
                align="ctr",
                valign="ctr",
                fill=CONNECTOR_LABEL_FILL,
                margin=0.02,
            )

    def _resources_by_id(self, model: dict[str, Any]) -> dict[str, dict[str, Any]]:
        resources: dict[str, dict[str, Any]] = {}
        for resource in model.get("resources") or []:
            if not isinstance(resource, dict):
                continue
            rid = normalize_lookup(resource.get("id"))
            if rid:
                resources[rid] = resource
        return resources

    def _is_database_resource(self, resource: dict[str, Any] | None) -> bool:
        if not isinstance(resource, dict):
            return False
        values = [
            resource.get("type"),
            resource.get("icon_key"),
            resource.get("label"),
            resource.get("placement"),
            resource.get("subnet"),
        ]
        return any(
            value
            and normalize_lookup(value) in {"database", "db", "data", "exadata", "db primary", "db standby"}
            or value
            and any(term in normalize_lookup(value) for term in ("database", "exadata"))
            for value in values
        )

    def _flow_label_counts(
        self, flows: list[dict[str, Any]]
    ) -> tuple[dict[tuple[str, str], int], dict[tuple[str, str], int]]:
        source_counts: dict[tuple[str, str], int] = {}
        target_counts: dict[tuple[str, str], int] = {}
        for flow in flows:
            if not isinstance(flow, dict):
                continue
            label = normalize_lookup(flow.get("label") or flow.get("type") or "")
            if not label:
                continue
            source = normalize_lookup(flow.get("from") or flow.get("source") or "")
            target = normalize_lookup(flow.get("to") or flow.get("target") or "")
            if source:
                source_counts[(source, label)] = source_counts.get((source, label), 0) + 1
            if target:
                target_counts[(target, label)] = target_counts.get((target, label), 0) + 1
        return source_counts, target_counts

    def _flow_label_group_key(
        self,
        source_id: str,
        target_id: str,
        label: str,
        source_counts: dict[tuple[str, str], int],
        target_counts: dict[tuple[str, str], int],
    ) -> tuple[str, str, str]:
        normalized_label = normalize_lookup(label)
        normalized_source = normalize_lookup(source_id)
        normalized_target = normalize_lookup(target_id)
        if source_counts.get((normalized_source, normalized_label), 0) > 1:
            return ("source", normalized_source, normalized_label)
        if target_counts.get((normalized_target, normalized_label), 0) > 1:
            return ("target", normalized_target, normalized_label)
        return (normalized_source, normalized_target, normalized_label)

    def _draw_arrow_once(
        self,
        slide: SlideBuilder,
        drawn: set[tuple[str, str, str]],
        horizontal_route_counts: dict[int, int],
        source_id: str,
        target_id: str,
        label: str,
        source: Box,
        target: Box,
        dash: str | None = None,
        arrow: bool = True,
    ) -> None:
        render_label = label if DRAW_CONNECTOR_LABELS else ""
        key = (source_id, target_id, render_label)
        if key in drawn:
            return
        drawn.add(key)
        start, end = self._edge_points(source, target)
        if self._should_use_elbow_connector(start, end):
            label_box = self._draw_elbow_arrow(
                slide,
                f"Flow {source_id} to {target_id}",
                start,
                end,
                horizontal_route_counts,
                dash,
                arrow,
                render_label,
            )
        else:
            slide.add_arrow(f"Flow {source_id} to {target_id}", start, end, dash=dash, arrow=arrow)
            label_box = self._flow_label_box(start, end, render_label)
        if render_label:
            slide.add_text(
                f"Flow label {source_id} to {target_id}",
                label_box,
                render_label,
                size_pt=CONNECTOR_LABEL_SIZE,
                color=CONNECTOR_LABEL_COLOR,
                bold=True,
                align="ctr",
                valign="ctr",
                fill=CONNECTOR_LABEL_FILL,
                margin=0.02,
            )

    def _should_use_elbow_connector(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> bool:
        dx = abs(end[0] - start[0])
        dy = abs(end[1] - start[1])
        return dx >= 0.65 and (dy <= 0.08 or dy >= 0.24)

    def _draw_elbow_arrow(
        self,
        slide: SlideBuilder,
        name: str,
        start: tuple[float, float],
        end: tuple[float, float],
        horizontal_route_counts: dict[int, int],
        dash: str | None,
        arrow: bool,
        label: str = "",
    ) -> Box:
        y_band = int(round(((start[1] + end[1]) / 2) * 10))
        route_index = horizontal_route_counts.get(y_band, 0)
        horizontal_route_counts[y_band] = route_index + 1

        direction = 1 if end[0] >= start[0] else -1
        if abs(end[1] - start[1]) >= 0.24:
            mid_offsets = (0.0, 0.18, -0.18, 0.34, -0.34)
            min_mid_x = min(start[0], end[0]) + 0.28
            max_mid_x = max(start[0], end[0]) - 0.28
            preferred_mid_x = (start[0] + end[0]) / 2 + mid_offsets[route_index % len(mid_offsets)]
            if min_mid_x <= max_mid_x:
                mid_x = min(max(preferred_mid_x, min_mid_x), max_mid_x)
            else:
                mid_x = (start[0] + end[0]) / 2
            points = [
                start,
                (mid_x, start[1]),
                (mid_x, end[1]),
                end,
            ]
            segments = list(zip(points, points[1:]))
            for index, (seg_start, seg_end) in enumerate(segments, start=1):
                last = index == len(segments)
                slide.add_arrow(
                    f"{name} segment {index}",
                    seg_start,
                    seg_end,
                    dash=dash,
                    arrow=arrow and last,
                )

            horizontal_segments = [
                segment
                for segment in segments
                if abs(segment[0][1] - segment[1][1]) <= 0.01
            ]
            label_w = self._flow_label_width(label)
            eligible_segments = [
                segment
                for segment in horizontal_segments
                if abs(segment[1][0] - segment[0][0]) >= label_w + 0.28
            ]
            if not eligible_segments:
                vertical_segments = [
                    segment
                    for segment in segments
                    if abs(segment[0][0] - segment[1][0]) <= 0.01
                ]
                vertical_segment = max(
                    vertical_segments,
                    key=lambda segment: abs(segment[1][1] - segment[0][1]),
                )
                return self._vertical_elbow_label_box(vertical_segment, direction, label)
            label_segment = eligible_segments[0]
            return self._elbow_label_box(
                label_segment[0],
                label_segment[1],
                start[1],
                label_segment[0][1],
                label,
            )

        offsets = (0.24, -0.24, 0.42, -0.42, 0.60, -0.60)
        offset = offsets[route_index % len(offsets)]
        jog_y = min(max(start[1] + offset, 0.55), SLIDE_H - 0.45)
        if abs(jog_y - start[1]) < 0.12:
            jog_y = min(max(start[1] - offset, 0.55), SLIDE_H - 0.45)

        mid_x = (start[0] + end[0]) / 2
        lead_x = min(max(start[0] + direction * 0.16, 0.2), SLIDE_W - 0.2)
        points = [
            start,
            (lead_x, start[1]),
            (lead_x, jog_y),
            (end[0], jog_y),
            end,
        ]
        segments = list(zip(points, points[1:]))
        for index, (seg_start, seg_end) in enumerate(segments, start=1):
            last = index == len(segments)
            slide.add_arrow(
                f"{name} segment {index}",
                seg_start,
                seg_end,
                dash=dash,
                arrow=arrow and last,
            )

        label_start = (mid_x, jog_y)
        label_end = (end[0], jog_y)
        if abs(label_end[0] - label_start[0]) < 0.2:
            label_start = (start[0], jog_y)
            label_end = (mid_x, jog_y)
        return self._elbow_label_box(label_start, label_end, start[1], jog_y, label)

    def _elbow_label_box(
        self,
        segment_start: tuple[float, float],
        segment_end: tuple[float, float],
        original_y: float,
        jog_y: float,
        label: str,
    ) -> Box:
        label_w = self._flow_label_width(label)
        label_h = 0.24
        min_x = min(segment_start[0], segment_end[0]) + label_w / 2 + 0.12
        max_x = max(segment_start[0], segment_end[0]) - label_w / 2 - 0.12
        preferred_x = (segment_start[0] + segment_end[0]) / 2
        if min_x <= max_x:
            cx = min(max(preferred_x, min_x), max_x)
        else:
            cx = preferred_x

        if jog_y >= original_y:
            y = jog_y + 0.08
        else:
            y = jog_y - label_h - 0.08
        y = min(max(y, 0.55), SLIDE_H - 0.35 - label_h)
        cx = min(max(cx, 0.2 + label_w / 2), SLIDE_W - 0.2 - label_w / 2)
        return Box(cx - label_w / 2, y, label_w, label_h)

    def _vertical_elbow_label_box(
        self,
        segment: tuple[tuple[float, float], tuple[float, float]],
        direction: int,
        label: str,
    ) -> Box:
        label_w = self._flow_label_width(label)
        label_h = 0.24
        x = segment[0][0] + 0.10 if direction >= 0 else segment[0][0] - label_w - 0.10
        y = (segment[0][1] + segment[1][1]) / 2 - label_h / 2
        x = min(max(x, 0.2), SLIDE_W - 0.2 - label_w)
        y = min(max(y, 0.55), SLIDE_H - 0.35 - label_h)
        return Box(x, y, label_w, label_h)

    def _flow_label_box(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        label: str = "",
    ) -> Box:
        mx = (start[0] + end[0]) / 2
        my = (start[1] + end[1]) / 2
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = math.hypot(dx, dy) or 1.0
        nx = -dy / length
        ny = dx / length
        if ny > 0:
            nx = -nx
            ny = -ny
        label_w = self._flow_label_width(label)
        label_h = 0.24
        offset = abs(nx) * label_w / 2 + abs(ny) * label_h / 2 + 0.07
        cx = min(max(mx + nx * offset, 0.2 + label_w / 2), SLIDE_W - 0.2 - label_w / 2)
        cy = min(max(my + ny * offset, 0.55 + label_h / 2), SLIDE_H - 0.35 - label_h / 2)
        return Box(cx - label_w / 2, cy - label_h / 2, label_w, label_h)

    def _flow_label_width(self, label: str) -> float:
        if not label:
            return 1.16
        units = sum(1.6 if ord(char) > 127 else 1.0 for char in label)
        return min(max(0.62 + units * 0.046, 0.92), 1.72)

    def _box_inside(self, item: Box, container: Box) -> bool:
        return (
            item.x >= container.x
            and item.y >= container.y
            and item.right <= container.right
            and item.bottom <= container.bottom
        )

    def _draw_icon_only(
        self,
        slide: SlideBuilder,
        icon_key: str,
        name: str,
        icon_box: Box,
    ) -> None:
        icon = self._resolve_icon(icon_key)
        if icon.asset:
            slide.add_picture(name, icon_box, icon.asset)
        else:
            self.icon_notes.add(f"{icon.key}: no extracted asset; badge omitted")

    def _draw_icon(
        self,
        slide: SlideBuilder,
        icon_key: str,
        label: str,
        icon_box: Box,
        label_width: float = 1.05,
        label_size: float = STANDARD_ICON_LABEL_SIZE,
    ) -> None:
        icon = self._resolve_icon(icon_key)
        show_external_label = True
        if icon.asset and icon.source_type != "rendered-shape":
            slide.add_picture(f"Icon {label}", icon_box, icon.asset)
        elif icon.source_type == "rendered-shape":
            placeholder_text = self._placeholder_text(icon.key, label)
            self._draw_placeholder_icon(
                slide,
                f"Rendered-shape placeholder {label}",
                icon_box,
                placeholder_text,
            )
            show_external_label = placeholder_text != label
            self.icon_notes.add(
                f"{icon.key}: rendered-shape source represented as editable placeholder"
            )
        else:
            self._draw_placeholder_icon(
                slide,
                f"Icon placeholder {label}",
                icon_box,
                self._placeholder_text(icon.key, icon.label),
            )
            self.icon_notes.add(f"{icon.key}: no extracted asset; placeholder shape used")

        if show_external_label:
            slide.add_text(
                f"Label {label}",
                Box(icon_box.cx - label_width / 2, icon_box.bottom, label_width, 0.22),
                label,
                size_pt=label_size,
                color="111827",
                align="ctr",
                valign="ctr",
                margin=0.01,
            )

    def _draw_placeholder_icon(
        self,
        slide: SlideBuilder,
        name: str,
        icon_box: Box,
        text: str,
    ) -> None:
        slide.add_shape(name, icon_box, "FFFFFF", "456575", 1.0, preset="roundRect")
        slide.add_text(
            f"{name} text",
            icon_box,
            text,
            size_pt=6.8,
            color="456575",
            bold=True,
            align="ctr",
            valign="ctr",
            margin=0.01,
        )

    def _placeholder_text(self, icon_key: str, label: str) -> str:
        if icon_key in GATEWAY_SHORT_LABELS:
            return GATEWAY_SHORT_LABELS[icon_key]
        if icon_key == "exadata-database-service":
            return "ExaDI"
        words = [word for word in re.split(r"[^A-Za-z0-9]+", label) if word]
        if len(words) >= 2:
            return "".join(word[0].upper() for word in words[:3])
        return (label[:5] or icon_key[:5]).upper()

    def _resolve_icon(self, requested_key: str) -> IconRef:
        canonical = self._canonical_icon_key(requested_key) or requested_key
        candidates = [canonical]
        fallback = self.icon_fallbacks.get(canonical)
        if fallback:
            candidates.append(self._canonical_icon_key(fallback) or fallback)

        for candidate in candidates:
            entry = self.icon_map.get(candidate)
            if not isinstance(entry, dict):
                continue
            raw_asset = str(entry.get("asset_path") or "")
            asset = self.skill_dir / raw_asset if raw_asset else None
            if asset and asset.exists():
                return IconRef(
                    candidate,
                    str(entry.get("label") or candidate),
                    asset,
                    str(entry.get("source_type") or "image"),
                )

        candidate = candidates[-1] if candidates else canonical
        entry = self.icon_map.get(candidate)
        label = candidate
        source_type = "missing"
        if isinstance(entry, dict):
            label = str(entry.get("label") or candidate)
            source_type = str(entry.get("source_type") or source_type)
        return IconRef(candidate, label, None, source_type)

    def _canonical_icon_key(self, value: Any) -> str:
        raw = str(value or "")
        if raw in self.icon_map and isinstance(self.icon_map.get(raw), dict):
            return raw
        normalized = normalize_lookup(raw)
        if normalized in self.icon_aliases:
            return self.icon_aliases[normalized]
        hyphenated = normalized.replace(" ", "-")
        if hyphenated in self.icon_map and isinstance(self.icon_map.get(hyphenated), dict):
            return hyphenated
        fallback = self.icon_fallbacks.get(raw) or self.icon_fallbacks.get(hyphenated)
        if fallback:
            return self._canonical_icon_key(fallback) or fallback
        return ""

    def _resource_icon_key(self, resource: dict[str, Any]) -> str:
        explicit = str(resource.get("icon_key") or "")
        if explicit:
            return self._canonical_icon_key(explicit) or explicit
        resource_type = str(resource.get("type") or "").lower()
        mapped = RESOURCE_ICON_KEYS.get(resource_type)
        if mapped:
            return self._canonical_icon_key(mapped) or mapped
        return (
            self._canonical_icon_key(resource_type)
            or self._canonical_icon_key(resource.get("label"))
            or "compute"
        )

    def _resource_icon_size(self, icon_key: str, cell_h: float) -> float:
        return STANDARD_ICON_SIZE

    def _ordered_subnets(self, model: dict[str, Any]) -> list[dict[str, Any]]:
        subnets = list((model.get("vcn") or {}).get("subnets") or [])

        def order(subnet: dict[str, Any]) -> tuple[int, str]:
            tier = str(subnet.get("tier") or subnet.get("type") or "").lower()
            subnet_type = str(subnet.get("type") or "").lower()
            key = tier if tier in TIER_ORDER else subnet_type
            return (TIER_ORDER.get(key, 10), str(subnet.get("name") or ""))

        return sorted(subnets, key=order)

    def _expand_resources(self, resources: list[dict[str, Any]]) -> list[dict[str, Any]]:
        expanded = []
        for resource in resources:
            try:
                count = max(int(resource.get("count") or 1), 1)
            except (TypeError, ValueError):
                count = 1
            base_label = str(resource.get("label") or resource.get("type") or "Resource")
            for index in range(count):
                label = base_label if count == 1 else f"{base_label} {index + 1}"
                expanded.append({"resource": resource, "label": label, "index": index + 1})
        return expanded

    def _gateway_y(
        self,
        key: str,
        gateway_type: str,
        subnet_boxes: dict[str, Box],
        vcn_box: Box,
    ) -> float:
        lower = {name.lower(): box for name, box in subnet_boxes.items()}
        if key == "internet-gateway":
            box = self._first_matching_box(lower, ["public", "edge", "dmz"])
            return (box.cy if box else vcn_box.y + 1.0) - 0.21
        if key == "nat-gateway":
            private_boxes = self._private_tier_boxes(subnet_boxes)
            box = private_boxes[0] if private_boxes else self._first_matching_box(lower, ["private", "app"])
            return (box.cy if box else vcn_box.cy) - 0.21
        if key == "service-gateway":
            box = self._first_matching_box(lower, ["data", "db", "database"])
            return (box.cy if box else vcn_box.cy) - 0.21
        if gateway_type in {"local-peering-gateway", "lpg"}:
            private_boxes = self._private_tier_boxes(subnet_boxes)
            if private_boxes:
                return private_boxes[0].cy - STANDARD_ICON_SIZE / 2
            return vcn_box.cy - 0.21
        if gateway_type in {
            "remote-peering-gateway",
            "remote-peering-connection",
            "rpg",
        } or key == "remote-peering-gateway":
            private_boxes = self._private_tier_boxes(subnet_boxes)
            if len(private_boxes) >= 2:
                return private_boxes[1].cy - STANDARD_ICON_SIZE / 2
            return vcn_box.cy - 0.21
        if key == "dynamic-routing-gateway" or gateway_type in {"drg", "dynamic-routing-gateway"}:
            box = self._first_matching_box(lower, ["management", "mgmt", "security", "inspection"])
            return (box.cy if box else vcn_box.cy) - 0.21
        if gateway_type in {"fastconnect", "fast-connect"} or key == "backbone":
            return vcn_box.cy - 0.21
        return vcn_box.cy - 0.21

    def _avoid_gateway_overlap(
        self,
        preferred_y: float,
        occupied: list[float],
        min_y: float,
        max_y: float,
        min_gap: float = 0.58,
    ) -> float:
        y = min(max(preferred_y, min_y), max_y)
        if not occupied:
            return y
        candidates = [y]
        for step in range(1, 7):
            candidates.extend([y + step * min_gap, y - step * min_gap])
        valid = [
            candidate
            for candidate in candidates
            if min_y <= candidate <= max_y
            and all(abs(candidate - other) >= min_gap for other in occupied)
        ]
        if valid:
            return min(valid, key=lambda candidate: abs(candidate - y))
        return y

    def _first_matching_box(self, boxes: dict[str, Box], terms: list[str]) -> Box | None:
        for term in terms:
            for name, box in boxes.items():
                if term in name:
                    return box
        return None

    def _private_tier_boxes(self, subnet_boxes: dict[str, Box]) -> list[Box]:
        private_boxes: list[Box] = []
        for name, box in subnet_boxes.items():
            normalized = normalize_lookup(name)
            if any(term in normalized for term in ("public", "edge", "dmz")):
                continue
            private_boxes.append(box)
        return sorted(private_boxes, key=lambda item: item.y)

    def _box_for_endpoint(self, endpoint: str) -> Box | None:
        key = endpoint.lower()
        if key in self.boxes:
            return self.boxes[key]
        normalized = normalize_lookup(endpoint)
        if normalized in self.boxes:
            return self.boxes[normalized]
        return self.boxes.get(endpoint)

    def _edge_points(
        self,
        source: Box,
        target: Box,
    ) -> tuple[tuple[float, float], tuple[float, float]]:
        dx = target.cx - source.cx
        dy = target.cy - source.cy
        if abs(dx) >= abs(dy):
            start = (source.right if dx >= 0 else source.x, source.cy)
            end = (target.x if dx >= 0 else target.right, target.cy)
        else:
            start = (source.cx, source.bottom if dy >= 0 else source.y)
            end = (target.cx, target.y if dy >= 0 else target.bottom)
        return start, end

    def _union_boxes(self, boxes: list[Box]) -> Box:
        x1 = min(box.x for box in boxes)
        y1 = min(box.y for box in boxes)
        x2 = max(box.right for box in boxes)
        y2 = max(box.bottom for box in boxes)
        return Box(x1, y1, x2 - x1, y2 - y1)

    def _synthetic_flows(self, model: dict[str, Any]) -> list[dict[str, str]]:
        resources = list(model.get("resources") or [])
        by_type = {str(resource.get("type") or ""): resource for resource in resources}
        flows: list[dict[str, str]] = []
        lb = by_type.get("load-balancer")
        bastion = by_type.get("bastion")
        db = by_type.get("exadata") or by_type.get("database")
        app = by_type.get("app-server") or by_type.get("web-server") or by_type.get("compute")

        if lb and lb.get("id"):
            flows.append({"from": "internet", "to": str(lb["id"]), "label": "HTTPS 443"})
        if lb and app and lb.get("id") and app.get("id"):
            flows.append({"from": str(lb["id"]), "to": str(app["id"]), "label": "App traffic"})
        if app and db and app.get("id") and db.get("id"):
            flows.append({"from": str(app["id"]), "to": str(db["id"]), "label": "Private DB"})
        if bastion and app and bastion.get("id") and app.get("id"):
            flows.append({"from": str(bastion["id"]), "to": str(app["id"]), "label": "Admin SSH"})
        if db and db.get("id") and "service-gateway" in self.boxes:
            flows.append({"from": str(db["id"]), "to": "service-gateway", "label": "Backup"})
        return flows

    def _summary_lines(self, model: dict[str, Any]) -> list[str]:
        vcns = self._model_vcns(model)
        if vcns:
            subnets = [
                subnet
                for vcn in vcns
                for subnet in vcn.get("subnets") or []
                if isinstance(subnet, dict)
            ]
            gateways = [
                gateway
                for vcn in vcns
                for gateway in vcn.get("gateways") or []
                if isinstance(gateway, dict)
            ]
        else:
            vcn = model.get("vcn") or {}
            subnets = list(vcn.get("subnets") or [])
            gateways = list(vcn.get("gateways") or [])
        resources = list(model.get("resources") or [])
        external_networks = self._external_networks(model)
        connections = list(model.get("connections") or [])
        return [
            f"Subnets: {len(subnets)}",
            f"Resources: {sum(max(int(r.get('count') or 1), 1) for r in resources)}",
            f"VCN-level gateways: {len(gateways)}",
            f"External networks: {len(external_networks)}",
            f"Network connections: {len(connections)}",
        ]

    def _section_text(self, title: str, items: list[Any]) -> str:
        lines = [title]
        for item in items:
            lines.append(f"- {item}")
        return "\n".join(lines)


def load_model(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("model JSON must be an object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a concise editable OCI architecture PPTX deck."
    )
    parser.add_argument("model_json", help="Path to the diagram model JSON file")
    parser.add_argument("output_pptx", help="Path to write the generated .pptx")
    args = parser.parse_args()

    model_path = Path(args.model_json)
    output_path = Path(args.output_pptx)
    if output_path.suffix.lower() != ".pptx":
        parser.error("output path must end with .pptx")

    skill_dir = Path(__file__).resolve().parents[1]
    try:
        model = load_model(model_path)
        Renderer(skill_dir).render(model, output_path)
    except Exception as exc:  # noqa: BLE001 - CLI should report a concise failure.
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    print(f"[OK] wrote {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
