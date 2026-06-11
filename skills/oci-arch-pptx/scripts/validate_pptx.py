#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED_PARTS = {
    "[Content_Types].xml",
    "ppt/presentation.xml",
}

DRAWINGML_TEXT_TAG = "{http://schemas.openxmlformats.org/drawingml/2006/main}t"
EMU_PER_INCH = 914400
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"
NS = {"a": NS_A, "p": NS_P}

LAYOUT_TOLERANCE_IN = 0.02
CONNECTOR_LABEL_OVERLAP_LIMIT_IN = 0.16
STANDARD_ICON_SIZE_IN = 0.48
STANDARD_ICON_LABEL_SIZE = "700"
VCN_BADGE_SIZE_IN = 0.30
SUBNET_BADGE_SIZE_IN = 0.23
EXPECTED_LABEL_LATIN_FONT = "Aptos"
EXPECTED_LABEL_EA_FONT = "Malgun Gothic"

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
    "mgmt": 5,
}

EDGE_TERMS = ("api gateway", "bastion", "load balancer", "waf")
SECURITY_TERMS = ("firewall", "network firewall")
APP_TERMS = ("app", "compute", "container", "function", "kubernetes", "oke", "was", "web")
DATA_TERMS = (
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
OSN_TERMS = (
    "audit",
    "bucket",
    "iam",
    "logging",
    "monitoring",
    "object storage",
    "service connector",
    "vault",
)
EXTERNAL_TERMS = ("customer data center", "customer premises", "on prem", "on premises", "cpe")

GATEWAY_ALIASES = {
    "fast-connect": ("FastConnect", "FC"),
    "fastconnect": ("FastConnect", "FC"),
    "internet-gateway": ("Internet Gateway", "IGW"),
    "nat-gateway": ("NAT Gateway", "NAT"),
    "service-gateway": ("Service Gateway", "SGW"),
    "drg": ("Dynamic Routing Gateway", "DRG"),
    "local-peering-gateway": ("Local Peering Gateway", "LPG"),
}

Requirement = tuple[str, str, tuple[str, ...]]


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


@dataclass(frozen=True)
class NamedElement:
    name: str
    kind: str
    slide_part: str
    element: ET.Element
    box: Box


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"file not found: {path}"]
    if path.suffix.lower() != ".pptx":
        errors.append(f"expected .pptx extension, got {path.suffix!r}")

    try:
        with zipfile.ZipFile(path) as package:
            names = set(package.namelist())
            for part in sorted(REQUIRED_PARTS):
                if part not in names:
                    errors.append(f"missing required part: {part}")

            slide_parts = sorted(
                name
                for name in names
                if name.startswith("ppt/slides/slide") and name.endswith(".xml")
            )
            if not slide_parts:
                errors.append("missing slide XML parts")

            if "[Content_Types].xml" in names:
                try:
                    content_types = ET.fromstring(package.read("[Content_Types].xml"))
                except ET.ParseError as exc:
                    errors.append(f"[Content_Types].xml parse error: {exc}")
                else:
                    errors.extend(validate_content_types(content_types, names))

            for xml_part in sorted(name for name in names if name.endswith(".xml")):
                try:
                    ET.fromstring(package.read(xml_part))
                except ET.ParseError as exc:
                    errors.append(f"{xml_part} parse error: {exc}")
    except zipfile.BadZipFile:
        return [f"not a valid PPTX zip package: {path}"]

    return errors


def validate_content_types(content_types: ET.Element, package_names: set[str]) -> list[str]:
    errors: list[str] = []
    defaults = {
        item.attrib.get("Extension", "").lower(): item.attrib.get("ContentType", "")
        for item in content_types.findall(f"{{{NS_CT}}}Default")
    }
    media_extensions = {
        Path(name).suffix.lower().lstrip(".")
        for name in package_names
        if name.startswith("ppt/media/") and Path(name).suffix
    }

    if "svg" in defaults and "svg" not in media_extensions:
        errors.append("[Content_Types].xml declares SVG media but no .svg part exists")
    if "svg" in media_extensions and defaults.get("svg") != "image/svg+xml":
        errors.append("[Content_Types].xml missing image/svg+xml default for .svg media")
    if "png" in media_extensions and defaults.get("png") != "image/png":
        errors.append("[Content_Types].xml missing image/png default for .png media")
    return errors


def validate_model_coverage(
    pptx_path: Path, model_path: Path
) -> tuple[int, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not model_path.exists():
        return 0, [f"model file not found: {model_path}"], warnings

    try:
        model = json.loads(model_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return 0, [f"model JSON parse error: {exc}"], warnings

    requirements, model_errors, model_warnings = collect_model_requirements(model)
    errors.extend(model_errors)
    warnings.extend(model_warnings)
    if not requirements:
        warnings.append("model contains no required labels for text coverage checks")

    try:
        slide_text = normalize_text("\n".join(extract_slide_text(pptx_path)))
    except (zipfile.BadZipFile, ET.ParseError) as exc:
        errors.append(f"could not extract slide text: {exc}")
        slide_text = ""

    for category, model_source, candidates in requirements:
        if any(label_is_present(candidate, slide_text) for candidate in candidates):
            continue
        errors.append(
            f"missing {category} label in slide text: "
            f"{' or '.join(candidates)} ({model_source})"
        )

    return len(requirements), errors, warnings


def validate_model_layout_rules(
    pptx_path: Path, model_path: Path
) -> tuple[int, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    checks = 0

    if not model_path.exists():
        return checks, [f"model file not found: {model_path}"], warnings
    try:
        model = json.loads(model_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return checks, [f"model JSON parse error: {exc}"], warnings
    if not isinstance(model, dict):
        return checks, ["model root must be a JSON object"], warnings

    elements = collect_named_elements(pptx_path, errors)
    if not elements:
        return checks, errors, warnings

    checks += validate_model_resource_containment(model, elements, errors, warnings)
    checks += validate_model_osn_presence(model, elements, errors)
    checks += validate_model_gateway_route_rules(model, errors, warnings)
    return checks, errors, warnings


def validate_layout_rules(pptx_path: Path) -> tuple[int, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    elements = collect_named_elements(pptx_path, errors)
    checks = 0

    if not elements:
        return checks, errors, warnings
    if "VCN boundary" not in elements:
        warnings.append("layout checks skipped: VCN boundary was not found")
        return checks, errors, warnings

    checks += validate_vcn_badge(elements, errors)
    checks += validate_subnet_badges(elements, errors)
    checks += validate_subnet_layout(elements, errors)
    checks += validate_standard_icon_sizes(elements, errors)
    checks += validate_oracle_service_network(elements, errors)
    checks += validate_icon_label_text(elements, errors)
    checks += validate_connector_labels(elements, errors)

    return checks, errors, warnings


def collect_named_elements(
    pptx_path: Path, errors: list[str]
) -> dict[str, list[NamedElement]]:
    result: dict[str, list[NamedElement]] = {}
    try:
        with zipfile.ZipFile(pptx_path) as package:
            slide_parts = sorted(
                (
                    name
                    for name in package.namelist()
                    if name.startswith("ppt/slides/slide") and name.endswith(".xml")
                ),
                key=slide_sort_key,
            )
            for slide_part in slide_parts:
                root = ET.fromstring(package.read(slide_part))
                for kind, tag in (
                    ("shape", "p:sp"),
                    ("picture", "p:pic"),
                    ("connector", "p:cxnSp"),
                ):
                    for element in root.findall(f".//{tag}", NS):
                        name = element_name(element)
                        box = element_box(element)
                        if not name or box is None:
                            continue
                        result.setdefault(name, []).append(
                            NamedElement(name, kind, slide_part, element, box)
                        )
    except (zipfile.BadZipFile, ET.ParseError) as exc:
        errors.append(f"could not extract layout elements: {exc}")
    return result


def validate_vcn_badge(
    elements: dict[str, list[NamedElement]], errors: list[str]
) -> int:
    checks = 0
    vcn = first_element(elements, "VCN boundary")
    badge = first_element(elements, "VCN badge")
    if badge is None:
        errors.append("missing layout element: VCN badge")
        return checks
    checks += assert_size(badge, VCN_BADGE_SIZE_IN, VCN_BADGE_SIZE_IN, errors)

    if vcn is not None:
        expected_x = vcn.box.right
        expected_y = vcn.box.y
        if approx_equal(badge.box.cx, expected_x) and approx_equal(badge.box.cy, expected_y):
            checks += 1
        else:
            errors.append(
                "VCN badge is not centered on VCN upper-right vertex: "
                f"badge center=({badge.box.cx:.3f}, {badge.box.cy:.3f}), "
                f"vertex=({expected_x:.3f}, {expected_y:.3f})"
            )
    return checks


def validate_subnet_badges(
    elements: dict[str, list[NamedElement]], errors: list[str]
) -> int:
    checks = 0
    subnet_indexes = sorted(
        int(match.group(1))
        for name in elements
        for match in [re.fullmatch(r"Subnet (\d+)", name)]
        if match
    )
    for index in subnet_indexes:
        for suffix in ("route table", "security list"):
            name = f"Subnet {index} {suffix} badge"
            badge = first_element(elements, name)
            if badge is None:
                errors.append(f"missing layout element: {name}")
                continue
            checks += assert_size(
                badge, SUBNET_BADGE_SIZE_IN, SUBNET_BADGE_SIZE_IN, errors
            )
    return checks


def validate_subnet_layout(
    elements: dict[str, list[NamedElement]], errors: list[str]
) -> int:
    checks = 0
    vcns = elements.get("VCN boundary") or []
    if not vcns:
        return checks

    subnets = [
        item
        for name, matches in elements.items()
        if re.fullmatch(r"Subnet \d+", name)
        for item in matches
    ]
    for subnet in subnets:
        if any(is_inside(subnet, vcn) for vcn in vcns):
            checks += 1
        else:
            errors.append(
                f"{subnet.name} is not inside any VCN boundary: "
                f"item=({subnet.box.x:.3f},{subnet.box.y:.3f},"
                f"{subnet.box.w:.3f},{subnet.box.h:.3f})"
            )

    for left_index, left in enumerate(subnets):
        for right in subnets[left_index + 1 :]:
            if boxes_overlap(left.box, right.box):
                errors.append(
                    f"{left.name} overlaps {right.name}: "
                    f"left=({left.box.x:.3f},{left.box.y:.3f},"
                    f"{left.box.w:.3f},{left.box.h:.3f}), "
                    f"right=({right.box.x:.3f},{right.box.y:.3f},"
                    f"{right.box.w:.3f},{right.box.h:.3f})"
                )
            else:
                checks += 1
    return checks


def validate_standard_icon_sizes(
    elements: dict[str, list[NamedElement]], errors: list[str]
) -> int:
    checks = 0
    for name, matches in sorted(elements.items()):
        if not name.startswith("Icon "):
            continue
        for item in matches:
            checks += assert_size(
                item, STANDARD_ICON_SIZE_IN, STANDARD_ICON_SIZE_IN, errors
            )
    return checks


def validate_oracle_service_network(
    elements: dict[str, list[NamedElement]], errors: list[str]
) -> int:
    checks = 0
    osn = first_element(elements, "Oracle Service Network boundary")
    if osn is None:
        return checks

    vcn = first_element(elements, "VCN boundary")
    if vcn is None:
        errors.append("Oracle Service Network exists but VCN boundary is missing")
    else:
        if approx_equal(osn.box.y, vcn.box.y) and approx_equal(osn.box.h, vcn.box.h):
            checks += 1
        else:
            errors.append(
                "Oracle Service Network must match VCN vertical span: "
                f"OSN y/h=({osn.box.y:.3f}, {osn.box.h:.3f}), "
                f"VCN y/h=({vcn.box.y:.3f}, {vcn.box.h:.3f})"
            )

    service_items: list[NamedElement] = []
    for name, matches in sorted(elements.items()):
        if not name.startswith("Icon "):
            continue
        for item in matches:
            if is_inside(item, osn):
                service_items.append(item)
                checks += assert_inside(item, osn, errors)

    if not service_items:
        errors.append("Oracle Service Network must contain at least one service icon")
    else:
        centers_y = [item.box.cy for item in service_items]
        centers_x = [item.box.cx for item in service_items]
        if len(set(round(y, 3) for y in centers_y)) == len(centers_y):
            checks += 1
        else:
            errors.append(
                "OSN service icons must use distinct vertical positions: "
                + ", ".join(f"{item.name} y={item.box.cy:.3f}" for item in service_items)
            )
        if max(centers_x) - min(centers_x) <= LAYOUT_TOLERANCE_IN:
            checks += 1
        else:
            errors.append(
                "OSN service icons must be vertically aligned: "
                + ", ".join(f"{item.name} x={item.box.cx:.3f}" for item in service_items)
            )

    return checks


def validate_icon_label_text(
    elements: dict[str, list[NamedElement]], errors: list[str]
) -> int:
    checks = 0
    for name, matches in sorted(elements.items()):
        if not name.startswith("Label "):
            continue
        for item in matches:
            sizes = {
                value
                for value in rpr_values(item.element, "sz")
                if value is not None
            }
            if sizes == {STANDARD_ICON_LABEL_SIZE}:
                checks += 1
            else:
                errors.append(
                    f"{item.name} must use {int(STANDARD_ICON_LABEL_SIZE) / 100:.1f}pt text; "
                    f"found {sorted(sizes) or ['<missing>']}"
                )

            latin_fonts = typeface_values(item.element, "latin")
            ea_fonts = typeface_values(item.element, "ea")
            if latin_fonts == {EXPECTED_LABEL_LATIN_FONT}:
                checks += 1
            else:
                errors.append(
                    f"{item.name} must use latin font {EXPECTED_LABEL_LATIN_FONT}; "
                    f"found {sorted(latin_fonts) or ['<missing>']}"
                )
            if ea_fonts == {EXPECTED_LABEL_EA_FONT}:
                checks += 1
            else:
                errors.append(
                    f"{item.name} must use EA font {EXPECTED_LABEL_EA_FONT}; "
                    f"found {sorted(ea_fonts) or ['<missing>']}"
                )
    return checks


def validate_connector_labels(
    elements: dict[str, list[NamedElement]], errors: list[str]
) -> int:
    checks = 0
    labels = [
        item
        for name, matches in elements.items()
        if name.startswith("Flow label ")
        for item in matches
    ]
    if not labels:
        return checks

    connectors = [
        item
        for name, matches in elements.items()
        if name.startswith("Flow ") and not name.startswith("Flow label ")
        for item in matches
    ]
    for label in labels:
        suffix = label.name.removeprefix("Flow label ")
        matching = [
            connector
            for connector in connectors
            if connector.name == f"Flow {suffix}"
            or connector.name.startswith(f"Flow {suffix} segment ")
        ]
        if not matching:
            continue
        inner_label = inset_box(label.box, 0.08, CONNECTOR_LABEL_OVERLAP_LIMIT_IN / 2)
        lines = [line for connector in matching if (line := connector_line_points(connector))]
        if any(segment_intersects_box(line[0], line[1], inner_label) for line in lines):
            errors.append(
                f"{label.name} overlaps connector line too much: line crosses label center band"
            )
        else:
            checks += 1
    return checks


def validate_model_resource_containment(
    model: dict[str, Any],
    elements: dict[str, list[NamedElement]],
    errors: list[str],
    warnings: list[str],
) -> int:
    checks = 0
    subnet_boxes = model_subnet_boxes(model, elements)
    if not subnet_boxes:
        warnings.append("model-aware containment skipped: no model subnet boxes were found")
        return checks

    assignments = expected_resource_subnets(model, subnet_boxes.keys())
    for resource_id, subnet_name in assignments.items():
        resource = resource_by_id(model).get(resource_id)
        if not resource or not subnet_name:
            continue
        subnet_box = subnet_boxes.get(subnet_name)
        if subnet_box is None:
            errors.append(f"expected subnet was not rendered for resource {resource_id}: {subnet_name}")
            continue
        labels = expected_resource_icon_names(resource)
        found_any = False
        for label in labels:
            icon_name = f"Icon {label}"
            matches = elements.get(icon_name) or []
            if not matches:
                continue
            found_any = True
            for item in matches:
                if is_inside(item, subnet_box):
                    checks += 1
                else:
                    errors.append(
                        f"{icon_name} is not inside expected subnet {subnet_name}: "
                        f"item=({item.box.x:.3f},{item.box.y:.3f},"
                        f"{item.box.w:.3f},{item.box.h:.3f}), "
                        f"subnet=({subnet_box.box.x:.3f},{subnet_box.box.y:.3f},"
                        f"{subnet_box.box.w:.3f},{subnet_box.box.h:.3f})"
                    )
        if not found_any:
            warnings.append(
                f"model-aware containment skipped for {resource_id}: "
                f"expected icon name(s) not found: {', '.join(labels)}"
            )
    return checks


def validate_model_osn_presence(
    model: dict[str, Any],
    elements: dict[str, list[NamedElement]],
    errors: list[str],
) -> int:
    checks = 0
    expected_services = expected_osn_services(model)
    osn = first_element(elements, "Oracle Service Network boundary")
    if expected_services and osn is None:
        errors.append("model declares OSN services but Oracle Service Network was not rendered")
        return checks
    if not expected_services and osn is not None:
        errors.append("Oracle Service Network was rendered but the model declares no OSN services")
        return checks
    if not expected_services:
        return checks + 1

    checks += 1
    for service in expected_services:
        candidates = expected_service_labels(service)
        if any(elements.get(f"Icon {label}") for label in candidates):
            checks += 1
        else:
            errors.append(
                "model OSN service was not rendered as an icon: "
                + " or ".join(candidates)
            )
    return checks


def validate_model_gateway_route_rules(
    model: dict[str, Any],
    errors: list[str],
    warnings: list[str],
) -> int:
    checks = 0
    subnets = ordered_subnets(model)
    gateway_types = model_gateway_types(model)
    public_subnets = [
        subnet for subnet in subnets if subnet_kind(subnet) in {"public", "edge", "dmz"}
    ]
    private_subnets = [
        subnet for subnet in subnets if subnet_kind(subnet) not in {"public", "edge", "dmz"}
    ]

    if public_subnets:
        if "internet-gateway" in gateway_types:
            checks += 1
        else:
            errors.append("public/edge subnets require an internet-gateway in vcn.gateways")

    if expected_osn_services(model):
        if "service-gateway" in gateway_types:
            checks += 1
        else:
            errors.append("OSN services require a service-gateway in vcn.gateways")

    if private_subnets:
        if "nat-gateway" in gateway_types or "service-gateway" in gateway_types:
            checks += 1
        else:
            warnings.append(
                "private subnets have no nat-gateway or service-gateway; "
                "private egress/service access may be incomplete"
            )

    if "nat-gateway" in gateway_types and not private_subnets:
        warnings.append("nat-gateway is present but the model has no private subnet")

    if "service-gateway" in gateway_types and not expected_osn_services(model):
        warnings.append("service-gateway is present but no OSN services are modeled")

    return checks


def collect_model_requirements(
    model: Any,
) -> tuple[list[Requirement], list[str], list[str]]:
    requirements: list[Requirement] = []
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(model, dict):
        return requirements, ["model root must be a JSON object"], warnings

    region = model.get("region")
    if isinstance(region, dict):
        add_requirement(
            requirements,
            "region",
            "region.name|region.oci_region",
            region.get("name"),
            region.get("oci_region"),
        )
    elif region is not None:
        errors.append("model region must be an object")

    vcns = model_vcns(model)
    vcn = model.get("vcn")
    subnets: list[Any] = []
    gateways: list[Any] = []
    if vcns:
        for index, item in enumerate(vcns):
            add_requirement(requirements, "vcn", f"vcns[{index}].name", item.get("name"))
            subnets.extend(list_field(item.get("subnets", []), f"vcns[{index}].subnets", errors))
            gateways.extend(list_field(item.get("gateways", []), f"vcns[{index}].gateways", errors))
    elif vcn is None:
        warnings.append("model has no vcn object; VCN/subnet coverage checks are limited")
    elif not isinstance(vcn, dict):
        errors.append("model vcn must be an object")
    else:
        add_requirement(requirements, "vcn", "vcn.name", vcn.get("name"))
        subnets = list_field(vcn.get("subnets", []), "vcn.subnets", errors)
        gateways = list_field(vcn.get("gateways", []), "vcn.gateways", errors)

    resources = list_field(model.get("resources", []), "resources", errors)
    subnet_names = collect_subnet_requirements(subnets, requirements, errors, warnings)
    resource_ids = collect_resource_requirements(
        resources, subnet_names, requirements, errors, warnings
    )
    check_subnet_resource_refs(subnets, resource_ids, errors, warnings)
    collect_gateway_requirements(gateways, requirements, errors)
    collect_osn_requirements(model, requirements, errors)
    collect_external_requirements(model, requirements, errors)
    collect_connection_requirements(model, requirements, errors)

    return requirements, errors, warnings


def collect_subnet_requirements(
    subnets: list[Any],
    requirements: list[Requirement],
    errors: list[str],
    warnings: list[str],
) -> set[str]:
    subnet_names: set[str] = set()
    if not subnets:
        warnings.append("model has no vcn.subnets entries; subnet label checks are skipped")
        return subnet_names

    for index, subnet in enumerate(subnets):
        if not isinstance(subnet, dict):
            errors.append(f"model vcn.subnets[{index}] must be an object")
            continue

        name = clean_string(subnet.get("name"))
        if not name:
            errors.append(
                f"model vcn.subnets[{index}] is missing name; "
                "cannot validate required subnet label"
            )
            continue
        if name in subnet_names:
            errors.append(f"duplicate subnet name in model: {name}")
        subnet_names.add(name)
        add_requirement(requirements, "subnet", f"vcn.subnets[{index}].name", name)

    return subnet_names


def collect_resource_requirements(
    resources: list[Any],
    subnet_names: set[str],
    requirements: list[Requirement],
    errors: list[str],
    warnings: list[str],
) -> set[str]:
    resource_ids: set[str] = set()
    if not resources:
        warnings.append("model has no resources entries; resource label checks are skipped")
        return resource_ids

    for index, resource in enumerate(resources):
        if not isinstance(resource, dict):
            errors.append(f"model resources[{index}] must be an object")
            continue

        resource_id = clean_string(resource.get("id"))
        label = clean_string(resource.get("label"))
        resource_type = clean_string(resource.get("type"))
        add_requirement(
            requirements,
            "resource",
            f"resources[{index}].label",
            label or resource_id or resource_type,
        )

        if resource_id:
            if resource_id in resource_ids:
                errors.append(f"duplicate resource id in model: {resource_id}")
            resource_ids.add(resource_id)
        elif not label:
            errors.append(
                f"model resources[{index}] is missing id and label; "
                "cannot validate required resource label"
            )

        subnet_ref = clean_string(resource.get("subnet"))
        placement = clean_string(resource.get("placement"))
        if not subnet_ref:
            icon_key = clean_string(resource.get("icon_key"))
            if not (placement or resource_type or icon_key):
                display = label or resource_id or f"resources[{index}]"
                warnings.append(
                    "model resource has no subnet, placement, type, or icon_key; "
                    f"visual containment is renderer-inferred for {display}"
                )
        elif subnet_names and subnet_ref not in subnet_names:
            errors.append(
                f"model resources[{index}].subnet references unknown subnet: "
                f"{subnet_ref}"
            )
        elif not subnet_names:
            warnings.append(
                f"model resources[{index}].subnet cannot be checked because "
                "the model has no named subnets"
            )

    return resource_ids


def check_subnet_resource_refs(
    subnets: list[Any],
    resource_ids: set[str],
    errors: list[str],
    warnings: list[str],
) -> None:
    for index, subnet in enumerate(subnets):
        if not isinstance(subnet, dict):
            continue

        refs = list_field(
            subnet.get("resources", []), f"vcn.subnets[{index}].resources", errors
        )
        for ref in refs:
            resource_id = clean_string(ref)
            if not resource_id:
                errors.append(
                    f"model vcn.subnets[{index}].resources contains a blank resource id"
                )
            elif resource_ids and resource_id not in resource_ids:
                errors.append(
                    f"model vcn.subnets[{index}].resources references unknown "
                    f"resource id: {resource_id}"
                )
            elif not resource_ids:
                warnings.append(
                    f"model vcn.subnets[{index}].resources cannot be checked "
                    "because the model has no resource ids"
                )


def collect_gateway_requirements(
    gateways: list[Any], requirements: list[Requirement], errors: list[str]
) -> None:
    for index, gateway in enumerate(gateways):
        if not isinstance(gateway, dict):
            errors.append(f"model vcn.gateways[{index}] must be an object")
            continue

        candidates = gateway_label_candidates(gateway)
        if candidates:
            add_requirement(
                requirements,
                "gateway",
                f"vcn.gateways[{index}].label|type",
                *candidates,
            )
        else:
            errors.append(
                f"model vcn.gateways[{index}] is missing label and type; "
                "cannot validate required gateway label"
            )


def collect_osn_requirements(
    model: dict[str, Any], requirements: list[Requirement], errors: list[str]
) -> None:
    osn_config = model.get("oracle_service_network")
    if isinstance(osn_config, dict):
        if osn_config.get("enabled") is not False:
            services = list_field(
                osn_config.get("services", []),
                "oracle_service_network.services",
                errors,
            )
            collect_service_label_requirements(
                services, "oracle_service_network.services", requirements, errors
            )
    elif isinstance(osn_config, list):
        collect_service_label_requirements(
            osn_config, "oracle_service_network", requirements, errors
        )
    elif osn_config not in (None, False, True):
        errors.append("model oracle_service_network must be an object, list, boolean, or null")

    if "public_services" in model:
        public_services = list_field(model.get("public_services"), "public_services", errors)
        collect_service_label_requirements(
            public_services, "public_services", requirements, errors
        )


def collect_service_label_requirements(
    services: list[Any],
    source: str,
    requirements: list[Requirement],
    errors: list[str],
) -> None:
    for index, service in enumerate(services):
        if isinstance(service, str):
            add_requirement(requirements, "public service", f"{source}[{index}]", service)
            continue
        if not isinstance(service, dict):
            errors.append(f"model {source}[{index}] must be a string or object")
            continue
        add_requirement(
            requirements,
            "public service",
            f"{source}[{index}].label|type",
            service.get("label"),
            service.get("id"),
            service.get("type"),
            service.get("icon_key"),
        )


def collect_external_requirements(
    model: dict[str, Any], requirements: list[Requirement], errors: list[str]
) -> None:
    external_networks = model.get("external_networks")
    if isinstance(external_networks, dict):
        external_networks = [external_networks]
    elif external_networks is None:
        external_networks = []
    elif not isinstance(external_networks, list):
        errors.append("model external_networks must be an object or list")
        external_networks = []

    for index, network in enumerate(external_networks):
        if isinstance(network, str):
            add_requirement(
                requirements, "external network", f"external_networks[{index}]", network
            )
            continue
        if not isinstance(network, dict):
            errors.append(f"model external_networks[{index}] must be a string or object")
            continue
        add_requirement(
            requirements,
            "external network",
            f"external_networks[{index}].label|type",
            network.get("label"),
            network.get("id"),
            network.get("type"),
        )

    on_premises = model.get("on_premises")
    if isinstance(on_premises, dict):
        add_requirement(
            requirements,
            "external network",
            "on_premises.label|type",
            on_premises.get("label"),
            on_premises.get("id"),
            on_premises.get("type"),
        )
    elif isinstance(on_premises, list):
        for index, network in enumerate(on_premises):
            if isinstance(network, dict):
                add_requirement(
                    requirements,
                    "external network",
                    f"on_premises[{index}].label|type",
                    network.get("label"),
                    network.get("id"),
                    network.get("type"),
                )
            elif isinstance(network, str):
                add_requirement(
                    requirements,
                    "external network",
                    f"on_premises[{index}]",
                    network,
                )
            else:
                errors.append(f"model on_premises[{index}] must be a string or object")
    elif on_premises not in (None, False, True):
        errors.append("model on_premises must be an object, list, boolean, or null")


def collect_connection_requirements(
    model: dict[str, Any], requirements: list[Requirement], errors: list[str]
) -> None:
    connections = list_field(model.get("connections", []), "connections", errors)
    for index, connection in enumerate(connections):
        if not isinstance(connection, dict):
            errors.append(f"model connections[{index}] must be an object")
            continue
        add_requirement(
            requirements,
            "connection",
            f"connections[{index}].label|type",
            connection.get("label"),
            connection.get("type"),
        )


def model_subnet_boxes(
    model: dict[str, Any],
    elements: dict[str, list[NamedElement]],
) -> dict[str, NamedElement]:
    boxes: dict[str, NamedElement] = {}
    for index, subnet in enumerate(ordered_subnets(model), start=1):
        name = clean_string(subnet.get("name")) if isinstance(subnet, dict) else ""
        element = first_element(elements, f"Subnet {index}")
        if name and element is not None:
            boxes[name] = element
    return boxes


def expected_resource_subnets(
    model: dict[str, Any],
    subnet_names: Any,
) -> dict[str, str]:
    available = list(subnet_names)
    by_id = resource_by_id(model)
    assignments: dict[str, str] = {}
    assigned: set[str] = set()

    for subnet in ordered_subnets(model):
        if not isinstance(subnet, dict):
            continue
        subnet_name = clean_string(subnet.get("name"))
        if not subnet_name:
            continue
        for resource_id in subnet.get("resources") or []:
            rid = clean_string(resource_id)
            resource = by_id.get(rid)
            if resource and not is_osn_resource(resource) and not is_external_resource(resource):
                assignments[rid] = subnet_name
                assigned.add(rid)

    for rid, resource in by_id.items():
        if rid in assigned or is_osn_resource(resource) or is_external_resource(resource):
            continue
        explicit = clean_string(resource.get("subnet"))
        if explicit in available:
            assignments[rid] = explicit
            assigned.add(rid)

    for rid, resource in by_id.items():
        if rid in assigned or is_osn_resource(resource) or is_external_resource(resource):
            continue
        subnet_name = inferred_resource_subnet(resource, available)
        if subnet_name:
            assignments[rid] = subnet_name
    return assignments


def resource_by_id(model: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for resource in model.get("resources") or []:
        if isinstance(resource, dict):
            rid = clean_string(resource.get("id"))
            if rid:
                result[rid] = resource
    return result


def expected_resource_icon_names(resource: dict[str, Any]) -> list[str]:
    try:
        count = max(int(resource.get("count") or 1), 1)
    except (TypeError, ValueError):
        count = 1
    base = clean_string(resource.get("label")) or clean_string(resource.get("type")) or "Resource"
    if count == 1:
        return [base]
    return [f"{base} {index}" for index in range(1, count + 1)]


def expected_osn_services(model: dict[str, Any]) -> list[Any]:
    services: list[Any] = []
    osn_config = model.get("oracle_service_network")
    if isinstance(osn_config, dict):
        if osn_config.get("enabled") is not False:
            services.extend(osn_config.get("services") or [])
    elif isinstance(osn_config, list):
        services.extend(osn_config)

    services.extend(model.get("public_services") or [])
    subnet_resource_ids = {
        clean_string(resource_id)
        for subnet in ordered_subnets(model)
        if isinstance(subnet, dict)
        for resource_id in subnet.get("resources") or []
    }
    for resource in model.get("resources") or []:
        if not isinstance(resource, dict):
            continue
        rid = clean_string(resource.get("id"))
        if rid not in subnet_resource_ids and is_osn_resource(resource):
            services.append(resource)
    return dedupe_services(services)


def dedupe_services(services: list[Any]) -> list[Any]:
    result: list[Any] = []
    seen: set[str] = set()
    for service in services:
        key = ""
        if isinstance(service, str):
            key = normalize_lookup(service)
        elif isinstance(service, dict):
            key = normalize_lookup(
                service.get("id")
                or service.get("label")
                or service.get("type")
                or service.get("icon_key")
            )
        if key and key not in seen:
            seen.add(key)
            result.append(service)
    return result


def expected_service_labels(service: Any) -> list[str]:
    if isinstance(service, str):
        return [service]
    if not isinstance(service, dict):
        return []
    labels = [
        clean_string(service.get("label")),
        clean_string(service.get("id")),
        clean_string(service.get("type")),
        clean_string(service.get("icon_key")),
    ]
    return [label for label in labels if label]


def ordered_subnets(model: dict[str, Any]) -> list[dict[str, Any]]:
    def order(subnet: dict[str, Any]) -> tuple[int, str]:
        tier = normalize_lookup(subnet.get("tier") or subnet.get("type"))
        subnet_type = normalize_lookup(subnet.get("type"))
        key = tier if tier in TIER_ORDER else subnet_type
        return (TIER_ORDER.get(key, 10), clean_string(subnet.get("name")))

    vcns = model_vcns(model)
    if vcns:
        result: list[dict[str, Any]] = []
        for vcn in vcns:
            subnets = [
                subnet
                for subnet in vcn.get("subnets") or []
                if isinstance(subnet, dict)
            ]
            result.extend(sorted(subnets, key=order))
        return result

    subnets = [
        subnet
        for subnet in (model.get("vcn") or {}).get("subnets") or []
        if isinstance(subnet, dict)
    ]
    return sorted(subnets, key=order)


def model_gateway_types(model: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for gateway in model_gateways(model):
        if not isinstance(gateway, dict):
            continue
        gateway_type = normalize_lookup(gateway.get("type")).replace(" ", "-")
        if gateway_type == "drg":
            gateway_type = "dynamic-routing-gateway"
        if gateway_type in {"fastconnect", "fast-connect"}:
            gateway_type = "fastconnect"
        if gateway_type:
            result.add(gateway_type)
    return result


def model_vcns(model: dict[str, Any]) -> list[dict[str, Any]]:
    vcns = model.get("vcns")
    if isinstance(vcns, list):
        return [vcn for vcn in vcns if isinstance(vcn, dict)]
    return []


def model_gateways(model: dict[str, Any]) -> list[Any]:
    vcns = model_vcns(model)
    if vcns:
        gateways: list[Any] = []
        for vcn in vcns:
            gateways.extend(vcn.get("gateways") or [])
        return gateways
    return list((model.get("vcn") or {}).get("gateways") or [])


def subnet_kind(subnet: dict[str, Any]) -> str:
    tier = normalize_lookup(subnet.get("tier"))
    subnet_type = normalize_lookup(subnet.get("type"))
    return tier or subnet_type


def inferred_resource_subnet(resource: dict[str, Any], subnet_names: list[str]) -> str:
    placement = resource_placement(resource)
    if placement in {"osn", "external"}:
        return ""
    if placement == "edge":
        return first_subnet_name_matching(subnet_names, ["public", "edge", "dmz", "ingress"])
    if placement == "security":
        return first_subnet_name_matching(
            subnet_names, ["security", "inspection", "firewall"]
        ) or first_subnet_name_matching(subnet_names, ["public", "edge", "dmz", "ingress"])
    if placement == "data":
        return first_subnet_name_matching(subnet_names, ["data", "database", "db", "storage"])
    if placement == "management":
        return first_subnet_name_matching(subnet_names, ["management", "mgmt"])
    return first_subnet_name_matching(
        subnet_names, ["app", "application", "private", "workload"]
    ) or (subnet_names[0] if subnet_names else "")


def first_subnet_name_matching(subnet_names: list[str], terms: list[str]) -> str:
    normalized_terms = [normalize_lookup(term) for term in terms]
    for term in normalized_terms:
        for name in subnet_names:
            if term and term in normalize_lookup(name):
                return name
    return ""


def resource_placement(resource: dict[str, Any]) -> str:
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
    if is_osn_value(explicit):
        return "osn"
    if is_external_value(explicit):
        return "external"

    text = normalize_lookup(
        " ".join(
            clean_string(resource.get(field))
            for field in ("icon_key", "type", "label", "notes")
        )
    )
    if any(term in text for term in OSN_TERMS):
        return "osn"
    if any(term in text for term in EXTERNAL_TERMS):
        return "external"
    if any(term in text for term in SECURITY_TERMS):
        return "security"
    if any(term in text for term in EDGE_TERMS):
        return "edge"
    if any(term in text for term in DATA_TERMS):
        return "data"
    if any(term in text for term in APP_TERMS):
        return "app"
    return "app"


def is_osn_resource(resource: dict[str, Any]) -> bool:
    for field in ("placement", "location", "network_scope"):
        if is_osn_value(resource.get(field)):
            return True
    subnet = resource.get("subnet")
    if subnet:
        return is_osn_value(subnet)
    return resource_placement(resource) == "osn"


def is_external_resource(resource: dict[str, Any]) -> bool:
    for field in ("placement", "location", "network_scope", "subnet"):
        if is_external_value(resource.get(field)):
            return True
    return resource_placement(resource) == "external"


def is_osn_value(value: Any) -> bool:
    return normalize_lookup(value) in {
        "osn",
        "oracle public services",
        "oracle service network",
        "oracle services network",
        "public services",
    }


def is_external_value(value: Any) -> bool:
    return normalize_lookup(value) in {
        "cpe",
        "customer data center",
        "customer dc",
        "external",
        "on prem",
        "on premise",
        "on premises",
        "onprem",
    }


def extract_slide_text(path: Path) -> list[str]:
    slide_texts: list[str] = []
    with zipfile.ZipFile(path) as package:
        slide_parts = sorted(
            (
                name
                for name in package.namelist()
                if name.startswith("ppt/slides/slide") and name.endswith(".xml")
            ),
            key=slide_sort_key,
        )
        for slide_part in slide_parts:
            root = ET.fromstring(package.read(slide_part))
            text_nodes = [
                element.text or ""
                for element in root.iter()
                if element.tag == DRAWINGML_TEXT_TAG
            ]
            slide_texts.append(" ".join(text_nodes))
    return slide_texts


def slide_sort_key(name: str) -> tuple[int, object]:
    match = re.search(r"slide(\d+)\.xml$", name)
    if match:
        return (0, int(match.group(1)))
    return (1, name)


def add_requirement(
    requirements: list[Requirement],
    category: str,
    model_source: str,
    *candidates: Any,
) -> None:
    cleaned: list[str] = []
    for candidate in candidates:
        text = clean_string(candidate)
        if text and text not in cleaned:
            cleaned.append(text)
    if cleaned:
        requirements.append((category, model_source, tuple(cleaned)))


def gateway_label_candidates(gateway: dict[str, Any]) -> tuple[str, ...]:
    candidates: list[str] = []
    label = clean_string(gateway.get("label"))
    gateway_type = clean_string(gateway.get("type"))
    if label:
        candidates.append(label)
    if gateway_type:
        candidates.extend(GATEWAY_ALIASES.get(gateway_type, (gateway_type,)))
    return tuple(candidates)


def list_field(value: Any, model_source: str, errors: list[str]) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    errors.append(f"model {model_source} must be a list")
    return []


def clean_string(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())


def normalize_lookup(value: Any) -> str:
    text = clean_string(value).replace("&nbsp;", " ").replace("&", " and ").casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def label_is_present(label: str, normalized_slide_text: str) -> bool:
    normalized_label = normalize_text(label)
    return bool(normalized_label and normalized_label in normalized_slide_text)


def element_name(element: ET.Element) -> str:
    name_node = element.find(".//p:cNvPr", NS)
    if name_node is None:
        return ""
    return clean_string(name_node.attrib.get("name"))


def element_box(element: ET.Element) -> Box | None:
    offset = element.find(".//a:off", NS)
    extent = element.find(".//a:ext", NS)
    if offset is None or extent is None:
        return None
    try:
        return Box(
            emu_to_inches(offset.attrib["x"]),
            emu_to_inches(offset.attrib["y"]),
            emu_to_inches(extent.attrib["cx"]),
            emu_to_inches(extent.attrib["cy"]),
        )
    except (KeyError, ValueError):
        return None


def first_element(
    elements: dict[str, list[NamedElement]], name: str
) -> NamedElement | None:
    matches = elements.get(name) or []
    return matches[0] if matches else None


def assert_size(
    item: NamedElement, expected_w: float, expected_h: float, errors: list[str]
) -> int:
    if approx_equal(item.box.w, expected_w) and approx_equal(item.box.h, expected_h):
        return 1
    errors.append(
        f"{item.name} size mismatch: expected {expected_w:.2f}x{expected_h:.2f}in, "
        f"found {item.box.w:.3f}x{item.box.h:.3f}in ({item.slide_part})"
    )
    return 0


def assert_inside(item: NamedElement, container: NamedElement, errors: list[str]) -> int:
    if is_inside(item, container):
        return 1
    errors.append(
        f"{item.name} must be inside {container.name}: "
        f"item=({item.box.x:.3f},{item.box.y:.3f},{item.box.w:.3f},{item.box.h:.3f}), "
        f"container=({container.box.x:.3f},{container.box.y:.3f},"
        f"{container.box.w:.3f},{container.box.h:.3f})"
    )
    return 0


def is_inside(item: NamedElement, container: NamedElement) -> bool:
    return (
        item.box.x >= container.box.x - LAYOUT_TOLERANCE_IN
        and item.box.y >= container.box.y - LAYOUT_TOLERANCE_IN
        and item.box.right <= container.box.right + LAYOUT_TOLERANCE_IN
        and item.box.bottom <= container.box.bottom + LAYOUT_TOLERANCE_IN
    )


def boxes_overlap(left: Box, right: Box) -> bool:
    return not (
        left.right <= right.x + LAYOUT_TOLERANCE_IN
        or right.right <= left.x + LAYOUT_TOLERANCE_IN
        or left.bottom <= right.y + LAYOUT_TOLERANCE_IN
        or right.bottom <= left.y + LAYOUT_TOLERANCE_IN
    )


def box_overlap(left: Box, right: Box) -> Box:
    x1 = max(left.x, right.x)
    y1 = max(left.y, right.y)
    x2 = min(left.right, right.right)
    y2 = min(left.bottom, right.bottom)
    if x2 <= x1 or y2 <= y1:
        return Box(0, 0, 0, 0)
    return Box(x1, y1, x2 - x1, y2 - y1)


def inset_box(box: Box, x: float, y: float) -> Box:
    inset_x = min(max(x, 0), box.w / 2)
    inset_y = min(max(y, 0), box.h / 2)
    return Box(
        box.x + inset_x,
        box.y + inset_y,
        max(box.w - 2 * inset_x, 0),
        max(box.h - 2 * inset_y, 0),
    )


def connector_line_points(
    item: NamedElement,
) -> tuple[tuple[float, float], tuple[float, float]] | None:
    xfrm = item.element.find(".//a:xfrm", NS)
    if xfrm is None:
        return None
    x1 = item.box.x
    y1 = item.box.y
    x2 = item.box.right
    y2 = item.box.bottom
    flip_h = xfrm.attrib.get("flipH") == "1"
    flip_v = xfrm.attrib.get("flipV") == "1"
    start = (x2 if flip_h else x1, y2 if flip_v else y1)
    end = (x1 if flip_h else x2, y1 if flip_v else y2)
    return start, end


def segment_intersects_box(
    start: tuple[float, float],
    end: tuple[float, float],
    box: Box,
) -> bool:
    if point_inside_box(start, box) or point_inside_box(end, box):
        return True
    corners = [
        (box.x, box.y),
        (box.right, box.y),
        (box.right, box.bottom),
        (box.x, box.bottom),
    ]
    edges = list(zip(corners, corners[1:] + corners[:1]))
    return any(segments_intersect(start, end, edge_start, edge_end) for edge_start, edge_end in edges)


def point_inside_box(point: tuple[float, float], box: Box) -> bool:
    return box.x <= point[0] <= box.right and box.y <= point[1] <= box.bottom


def segments_intersect(
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
) -> bool:
    def orientation(
        p: tuple[float, float],
        q: tuple[float, float],
        r: tuple[float, float],
    ) -> float:
        return (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])

    def on_segment(
        p: tuple[float, float],
        q: tuple[float, float],
        r: tuple[float, float],
    ) -> bool:
        return (
            min(p[0], r[0]) - LAYOUT_TOLERANCE_IN <= q[0] <= max(p[0], r[0]) + LAYOUT_TOLERANCE_IN
            and min(p[1], r[1]) - LAYOUT_TOLERANCE_IN <= q[1] <= max(p[1], r[1]) + LAYOUT_TOLERANCE_IN
        )

    o1 = orientation(a1, a2, b1)
    o2 = orientation(a1, a2, b2)
    o3 = orientation(b1, b2, a1)
    o4 = orientation(b1, b2, a2)
    if o1 * o2 < 0 and o3 * o4 < 0:
        return True
    if abs(o1) <= LAYOUT_TOLERANCE_IN and on_segment(a1, b1, a2):
        return True
    if abs(o2) <= LAYOUT_TOLERANCE_IN and on_segment(a1, b2, a2):
        return True
    if abs(o3) <= LAYOUT_TOLERANCE_IN and on_segment(b1, a1, b2):
        return True
    if abs(o4) <= LAYOUT_TOLERANCE_IN and on_segment(b1, a2, b2):
        return True
    return False


def rpr_values(element: ET.Element, attribute: str) -> list[str | None]:
    return [node.attrib.get(attribute) for node in element.findall(".//a:rPr", NS)]


def typeface_values(element: ET.Element, tag: str) -> set[str]:
    return {
        clean_string(node.attrib.get("typeface"))
        for node in element.findall(f".//a:{tag}", NS)
        if clean_string(node.attrib.get("typeface"))
    }


def emu_to_inches(value: str) -> float:
    return int(value) / EMU_PER_INCH


def approx_equal(left: float, right: float, tolerance: float = LAYOUT_TOLERANCE_IN) -> bool:
    return abs(left - right) <= tolerance


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate PPTX package structure and optional OCI model coverage."
    )
    parser.add_argument("pptx_file", help="Path to a .pptx file")
    parser.add_argument(
        "--model",
        help=(
            "Path to a diagram-model JSON file. When provided, required "
            "region, VCN, subnet, gateway, and resource labels are checked "
            "against slide text."
        ),
    )
    args = parser.parse_args()

    path = Path(args.pptx_file)
    errors = validate(path)
    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1

    print(f"[OK] valid PPTX package structure: {path}")

    layout_checks, layout_errors, layout_warnings = validate_layout_rules(path)
    for error in layout_errors:
        print(f"[ERROR] {error}")
    for warning in layout_warnings:
        print(f"[WARN] {warning}")
    if layout_errors:
        return 1
    if layout_checks:
        print(f"[OK] OCI diagram layout rules: {layout_checks} checks passed")

    if args.model:
        model_path = Path(args.model)
        checked_labels, model_errors, warnings = validate_model_coverage(path, model_path)
        for error in model_errors:
            print(f"[ERROR] {error}")
        for warning in warnings:
            print(f"[WARN] {warning}")
        if model_errors:
            return 1
        print(
            "[OK] model-aware text coverage: "
            f"{checked_labels} required label checks passed"
        )

        model_layout_checks, model_layout_errors, model_layout_warnings = (
            validate_model_layout_rules(path, model_path)
        )
        for error in model_layout_errors:
            print(f"[ERROR] {error}")
        for warning in model_layout_warnings:
            print(f"[WARN] {warning}")
        if model_layout_errors:
            return 1
        if model_layout_checks:
            print(
                "[OK] model-aware layout rules: "
                f"{model_layout_checks} checks passed"
            )
        print(
            "[INFO] model-aware scope: validates model references, slide text "
            "coverage, resource containment, OSN presence, and gateway combinations; "
            "visual preview QA is still recommended for dense diagrams"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
