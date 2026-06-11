---
name: oci-arch-pptx
description: Create or edit Oracle Cloud Infrastructure architecture diagrams as editable PowerPoint PPTX decks from natural-language requests. Use when Codex is asked to turn Korean or English OCI architecture descriptions into PPTX architecture slides, choose OCI service icons from a PowerPoint icon toolkit, apply Oracle Well-Architected and networking best practices, produce customer-ready OCI diagrams, or review OCI PPTX architecture outputs for correctness.
---

# OCI Architecture PPTX

## Overview

Use this skill to convert a user's natural-language OCI architecture request into a structured architecture model and an editable PowerPoint deck. The output should favor Oracle-recommended network segmentation, high availability, security controls, and OCI Architecture Diagram Toolkit icons from the bundled PowerPoint asset.

## Workflow

1. Parse the user request into a structured model.
   - Preserve explicit user choices.
   - Mark assumptions instead of silently inventing requirements.
   - Read `references/diagram-model.md` when creating or validating the model.

2. Apply OCI architecture guidance.
   - Read `references/oci-best-practices.md` before finalizing topology choices.
   - Prefer regional subnets unless the user asks for AD-specific subnets.
   - Keep databases and application backends in private subnets.
   - Use public or DMZ subnets only for internet-facing entry points such as public LoadBalancers and bastion access.
   - When both Web and App tiers are redundant, model the traffic chain as Public LoadBalancer -> Web backend set and Private/Internal LoadBalancer -> App backend set; do not pin individual Web nodes directly to individual App nodes unless the user explicitly requests that pattern.
   - Add NSG/security-rule notes for LoadBalancer to backend, bastion to private targets, app to database, and private egress.

3. Map services to OCI PowerPoint icons.
   - Use `assets/OCI_Icons.pptx` as the local OCI icon/template source.
   - Use the local draw.io library as a secondary vector source when PowerPoint icons are shape-only or unreliable.
   - Read `references/icon-source.md` for icon source rules and common resource mappings.
   - Use `references/icon-map.json` for generated `icon_key -> asset_path` mappings.
   - Resolve model `icon_key`, `type`, and service labels through `icon-map.json` keys, aliases, labels, and draw.io source titles before falling back to generic service-family icons.
   - If an exact icon is unavailable, use the closest OCI service-family icon and record the substitution.
   - Treat `source_type: "shape-label"` entries as found in the source deck but not directly extractable as image assets.
   - Treat `source_type: "rendered-shape"` entries as raster fallbacks. If preview rendering shows those crops are unreadable, use visible editable placeholders and record that substitution.
   - Treat `source_type: "drawio-vector"` entries as SVG assets extracted from draw.io stencils.
   - Treat `source_type: "drawio-raster"` entries as PNG fallbacks rendered from draw.io SVG assets for PPTX preview compatibility.

4. Render the PPTX deck.
   - If the Presentations skill/artifact-tool runtime is available, use it for editable PPTX generation and preview QA.
   - Produce a concise deck by default: title slide, architecture diagram slide, assumptions/best-practice notes slide.
   - Use layered slide structure: Region, Availability Domain or Fault Domain, VCN, Subnets, Gateways/Security, Workloads, Data, Annotations.
   - Use containment from outside to inside: Region > AD/FD if shown > VCN > subnet > resources.
   - Use `references/container-style-map.json` for OCI toolkit-derived container line, fill, dash, and label styling.
   - Read `references/connection-line-policy.md` when creating or modifying connector routing, line styling, or connector labels.
   - Put internet-facing resources on the Edge/Public subnet, network firewall on Security/Inspection when present, private compute/application services on App/Private, database/data services on Data/Private, Oracle public services in OSN, and customer/on-prem endpoints outside the Region.
   - For redundant Web/App tiers, show the public LoadBalancer in Edge/Public with Web servers as its backend set, and show a private/internal LoadBalancer in the private App tier with App servers as its backend set.
   - Preserve explicit `subnet` assignments; otherwise use `placement`, then infer placement from service `type`, `icon_key`, and `label`.
   - Label all subnets and tiers. Avoid connector labels on dense architecture slides unless the user explicitly asks for them; keep protocol or security-rule details in notes instead.
   - Include Korean labels when the user writes Korean unless they request English.
   - Keep all icons, labels, containers, arrows, and notes editable in PowerPoint whenever practical.

5. Validate output.
   - Run `scripts/validate_pptx.py <file.pptx>` after generating a file.
   - When a model JSON is available, run `scripts/validate_pptx.py <file.pptx> --model <model.json>` to check required text coverage for region, VCN, subnets, gateways, and resources.
   - The validator also checks renderer layout invariants for generated decks: VCN/Route Table/Security List badge sizes, subnet containment/non-overlap, standard OCI icon size, OSN vertical span and service icon alignment, connector-label overlap, and icon label font sizing.
   - With `--model`, the validator additionally checks expected resource-to-subnet containment, OSN presence only when modeled, and public/private subnet gateway combinations.
   - Check that the PPTX package is valid, has PowerPoint presentation parts, and contains at least one slide.
   - Render/preview the deck when the presentation runtime is available and inspect slide layout for overlap, missing resources, and readability.
   - Review best-practice deviations and report them as notes, not hidden changes.

## Diagram Layout Rules

Use this hierarchy for the main architecture slide: Region > VCN > Subnet > Service. The rendered diagram should make this nesting visually obvious.

```text
Region
  VCN
    Edge/Public Subnet
      LoadBalancer, Bastion, other internet-facing entry points
    App/Private Subnet
      Compute, web, WAS, application services
    Data/Private Subnet
      Database, Exadata, storage-sensitive services
```

- Draw Region as the outer boundary. Draw the VCN as the primary inner boundary.
- Place subnets inside the VCN in traffic order: Edge/Public, Security/Inspection, App/Private, Data/Private, Management. Use a single vertical stack up to four subnets; for five or more subnets, use a VCN-internal grid unless the model explicitly sets `layout.subnet_columns`.
- Put the VCN icon centered on the VCN container's upper-right vertex without a text label.
- Put Route Table and Security List icons tightly against each subnet container's upper-right corner without text labels.
- Put an Oracle Service Network container to the right of the VCN with the same vertical size as the VCN when Oracle public services are represented. Label the container `OSN` to avoid narrow-box line wrapping.
- Place the model's `oracle_service_network.services` or `public_services` icons vertically inside the Oracle Service Network. Do not draw Oracle Service Network services that are not present in the model.
- When a resource has no explicit subnet, place API Gateway, LoadBalancer, Bastion, and WAF in Edge/Public; Network Firewall in Security/Inspection when available; Compute, Functions, OKE, and app services in App/Private; Database, Exadata, MySQL, NoSQL, Data Flow, and Database Management in Data/Private; IAM, Audit, Object Storage, Logging, Monitoring, Vault, and related public services in Oracle Service Network.
- When Web and App tiers are both duplicated for HA, show Public LoadBalancer -> Web Server 1/2 and Private/Internal LoadBalancer -> App Server 1/2. Prefer naming the private LoadBalancer clearly; avoid connector labels in dense diagrams.
- Keep non-badge OCI service icons at a consistent larger size; do not resize the VCN, Route Table, or Security List corner badges unless requested.
- Place services only inside their owning subnet unless the resource is external to OCI or is a VCN-level gateway.
- Place VCN-level gateways inside the Region and adjacent to the VCN edge: IGW/NAT/DRG on the left side when shown, Service Gateway on the boundary between VCN and OSN when shown.
- Put external clients, internet actors, On-Prem, CPE, and Customer Data Center endpoints outside the Region boundary. Render Internet Users with the `user` icon, not a cloud shape. Connect On-Prem/CPE to DRG with `connections` entries such as FastConnect or VPN.
- Keep gateway labels short (`IGW`, `NAT`, `DRG`, `SGW`) when space is tight, and expand the meaning in slide notes.
- Keep arrows sparse: show only the primary ingress path, admin path through bastion, private app-to-data path, and private egress/service-access path when relevant. If these lines reduce readability, omit connection lines from the diagram slide and keep flow details in notes.
- Render network circuits (`connections`, FastConnect, VPN) as connector lines; render workload/data traffic (`flows`) as arrows.
- When connection lines are hidden for readability, keep only DB-to-DB `DataGuard` as a straight labeled connection line when Data Guard is modeled.
- When several horizontal connector lines would overlap or run through the same corridor, prefer orthogonal elbow connectors with staggered offsets instead of stacking straight horizontal lines.
- Do not render connector labels by default in dense diagrams. If protocol labels such as `HTTPS 443` or `SQL*Net` are required, use them only when they improve readability and do not collide with icons, containers, or lines.

## Subagents

Use subagents only when the environment supports them or the user asks for parallel validation. Read `references/subagents.md` before delegating; if subagents are unavailable, execute the same contracts sequentially in the main agent.

The main agent remains the orchestrator: prepare or update the model, assign isolated output paths and file ownership, integrate findings, choose the final deck path, run final validation, and report caveats to the user.

For complex diagrams, renderer changes, or validation hardening, use the standard parallel flow in `references/subagents.md`:

- `pptx-renderer-engineer`: generate or patch editable PPTX output from the approved model at an assigned path; edit `scripts/generate_pptx.py` only when explicitly assigned.
- `validation-engineer`: independently validate PPTX package structure, model coverage, layout invariants, connector labels, OSN behavior, gateway combinations, and fixture coverage; edit validator scripts or fixtures only when explicitly assigned.
- `intake-normalizer`: convert natural language to architecture JSON.
- `oci-best-practice-architect`: review topology against Oracle guidance.
- `icon-librarian`: map model resources and OSN services to OCI toolkit icons.

Do not let subagents overwrite the final user-facing PPTX, silently change architecture semantics, or report directly to the user. Always run the final validation commands in the orchestrator context even if a subagent already ran them.

## Example

User request:

```text
서울리전 - 서브넷 3개: 퍼블릭, 프라이빗 APP, 프라이빗 DB.
퍼블릭 서브넷에 로드밸런서와 배스천.
프라이빗 APP: 웹, 와스 2개씩.
프라이빗 DB: ExaDI.
```

Expected modeling choices:

- Region: `ap-seoul-1`.
- One VCN with three regional subnets.
- Public/DMZ subnet: public LoadBalancer, bastion, internet gateway.
- Private APP subnet: two web servers and two WAS/application servers distributed across fault domains when represented.
- Private DB subnet: Exadata Database on Dedicated Infrastructure, marked private, with service gateway/Object Storage backup path if shown.
- Security notes: no public DB access, backend accepts traffic from LoadBalancer only, private egress through NAT/service gateway, SSH through bastion from authorized CIDR only.

Expected PPTX shape:

- Slide 1: title and scope.
- Slide 2: full-page architecture diagram using OCI iconography.
- Slide 3: assumptions, security notes, and best-practice deviations if any.

## Output Contract

When finishing a diagram task, provide:

- Path to the generated `.pptx` file.
- Short assumption list.
- Short best-practice notes or deviations.
- Validation command result.
- Preview/render status if available.

## Resources

- `assets/OCI_Icons.pptx`: local OCI Architecture Diagram Toolkit PowerPoint source.
- `references/oci-best-practices.md`: Oracle best-practice checklist and source URLs.
- `references/diagram-model.md`: intermediate JSON model contract.
- `references/icon-source.md`: icon source and common icon mapping policy.
- `references/icon-aliases.json`: required icon keys, aliases, and fallback keys for extraction.
- `references/icon-map.json`: generated icon mapping from the bundled PPTX.
- `references/icon-inventory.json`: generated slide, text, picture, and candidate inventory for review.
- `references/drawio-icon-inventory.json`: generated draw.io library match and SVG extraction inventory.
- `references/container-style-map.json`: generated OCI draw.io Physical Grouping style map for Region, AD, FD, VCN, and subnet containers.
- `references/connection-line-policy.md`: connector line, elbow-routing, arrowhead, and label policy based on OCI toolkit sample slides 29 and 30.
- `references/subagents.md`: subagent workflow and role contracts.
- `scripts/extract_oci_icons.py`: extracts image-based icon mappings from `assets/OCI_Icons.pptx`.
- `scripts/extract_drawio_icons.py`: extracts selected or all service SVG assets from the local OCI draw.io `OCI Library.xml` and can register PNG fallback paths.
- `scripts/finalize_drawio_png_icons.py`: converts QuickLook-rendered `*.svg.png` files to `*.drawio.png` and removes border-connected white canvas backgrounds.
- `scripts/extract_drawio_container_styles.py`: extracts container line/fill/dash/label styles from the local OCI draw.io `OCI Library.xml`.
- `scripts/generate_pptx.py`: first deterministic pure-OOXML PPTX renderer for the standard Region > VCN > Subnet > Service layout.
- `scripts/render_shape_icons.py`: renders shape-only icon labels to PNG fallbacks when image assets are unavailable.
- `scripts/validate_pptx.py`: PPTX package validator with optional model-aware text coverage checks.
- `fixtures/validation/`: deterministic validation fixtures.
- `assets/extracted-icons/`: generated image assets referenced by `icon-map.json`.
