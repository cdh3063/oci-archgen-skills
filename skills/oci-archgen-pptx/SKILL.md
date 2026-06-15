---
name: oci-archgen-pptx
description: Create or edit Oracle Cloud Infrastructure architecture diagrams as editable PowerPoint PPTX decks from natural-language requests. Use when Codex is asked to turn Korean or English OCI architecture descriptions into PPTX architecture slides, choose OCI service icons from a PowerPoint icon toolkit, apply Oracle Well-Architected and networking best practices, produce customer-ready OCI diagrams, or review OCI PPTX architecture outputs for correctness.
---

# OCI Architecture PPTX

## Overview

Use this skill to convert a user's natural-language OCI architecture request into a structured architecture model and an editable PowerPoint deck. The output should favor Oracle-recommended network segmentation, high availability, security controls, and OCI Architecture Diagram Toolkit icons from the bundled PowerPoint asset.

## Workflow

1. Parse the user request into a structured model.
   - Preserve explicit user choices.
   - Mark assumptions instead of silently inventing requirements.
   - Treat model `language` as the input/narrative language for slides 3 and 4, not as permission to localize architecture diagram labels.
   - Keep architecture-facing labels in English: deck title, diagram title, container labels, subnet labels, resource labels, gateway labels, connector labels, and model-visible service labels.
   - Read `references/diagram-model.md` when creating or validating the model.
   - Read `references/rendering-guidelines.md` before creating or reviewing any generated architecture deck.
   - Read `references/consistency-guidelines.md` before creating or reviewing any model that uses multiple regions, multiple VCNs, DR, custom renderer paths, or nonstandard container names.
   - Read `references/odb-aws-guidelines.md` when the request mentions Oracle Database@AWS, ODB@AWS, OD@AWS, or Oracle Database at AWS.

2. Apply OCI architecture guidance.
   - Read `references/oci-best-practices.md` before finalizing topology choices.
   - Follow OCI/cloud architecture best practices by default. Do not weaken segmentation, private placement, HA, or security controls unless the user explicitly requests a nonrecommended design, and then record it as a best-practice deviation.
   - Prefer regional subnets unless the user asks for AD-specific subnets.
   - Keep Web, App, and DB workloads in private subnets. Never place Web, App, DB, MySQL, Exadata, Autonomous Database, or application compute resources in a Public Subnet.
   - Use Public Subnet only for internet-facing entry points such as Public Load Balancer, WAF/API Gateway when requested, and Bastion.
   - Always include Bastion in the Public Subnet for OCI architecture diagrams.
   - If the overall diagram has substantial unused left/right whitespace, render OSN to use that space. When OSN is rendered, include `IAM` and `Audit`; if any DB is present, also include `Object Storage`.
   - When both Web and App tiers are redundant, model the traffic chain as Public LoadBalancer -> Web backend set and Private/Internal LoadBalancer -> App backend set; do not pin individual Web nodes directly to individual App nodes unless the user explicitly requests that pattern.
   - For two-VCN DR, use top-level `vcns`. If both VCNs are in the same region, model Local Peering Gateway (`LPG`); if regions differ, model Remote Peering Gateway/Connection (`RPG`).
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
   - Apply `references/rendering-guidelines.md` to every generated deck, including OCI-only and Oracle Database@AWS decks.
   - Produce a concise deck by default: title slide, architecture diagram slide, assumptions/best-practice notes slide, and operational/best-practice checkpoint slide.
   - Render every generated deck's title slide using the `assets/OCI_Icons.pptx` slide 1 title-page form: Oracle-branded white cover, Oracle logo placement, large architecture title, concise subtitle, and small bottom metadata. Do not make AWS or other non-OCI vendor branding the main cover signal even for multicloud diagrams.
   - Use layered slide structure: Region, Availability Domain or Fault Domain, VCN, Subnets, Gateways/Security, Workloads, Data, Annotations.
   - Use containment from outside to inside: Region > AD/FD if shown > VCN > subnet > resources.
   - When on-premises IDC, customer data center, CPE, FastConnect, or VPN connectivity is requested, draw the external customer network as a left-side network container using the same OCI Region container visual treatment. Keep On-Prem/CPE icons inside that container.
   - Use `references/container-style-map.json` for OCI toolkit-derived container line, fill, dash, and label styling.
   - Read `references/connection-line-policy.md` when creating or modifying connector routing, line styling, or connector labels.
   - Put internet-facing entry resources and Bastion on the Edge/Public subnet, network firewall on Security/Inspection when present, private Web/App services on Web/App private subnets, database/data services on Data/Private, Oracle public services in OSN, and customer/on-prem endpoints outside the Region.
   - For redundant Web/App tiers, show the public LoadBalancer in Edge/Public with Web servers as its backend set, and show a private/internal LoadBalancer in the private App tier with App servers as its backend set.
   - Preserve explicit `subnet` assignments; otherwise use `placement`, then infer placement from service `type`, `icon_key`, and `label`.
   - Label all subnets and tiers. Avoid connector labels on dense architecture slides unless the user explicitly asks for them; keep protocol or security-rule details in notes instead.
   - Keep visible subnet labels concise: use `Public`, `Private-Web`, `Private-App`, `Private-DB`, `Security`, or `Private-Mgmt`. Do not render verbose combined labels such as `Seoul Private App - Private - APP`, repeated public/private words, or CIDR suffixes in the subnet header.
   - Always show the external actor as a `User` icon labeled `User`, not `Internet Users`.
   - Render architecture component labels at 11 pt by default. If 11 pt text does not fit, resize or reposition containers/icons, shorten the label, or move details to notes rather than reducing the architecture label font.
   - Render all diagram label text boxes with transparent/no-fill backgrounds. Do not place white label canvases behind connector labels, service labels, gateway labels, subnet labels, or container labels.
   - Use the standard icon size by default, but reduce service icon size when icons or labels would overflow their subnet/container.
   - If a single-column subnet stack lacks vertical room and the VCN has horizontal room, use a 2 x N subnet layout instead of forcing all subnets into 1 x N.
   - Put a concise AI-output verification disclaimer in the architecture diagram slide footer, styled at 10 pt in red and left-aligned.
   - Keep architecture labels in English even when the user writes in Korean. Render slides 3 and 4 narrative content in the user's input language unless they request a different language.
   - Keep all icons, labels, containers, arrows, and notes editable in PowerPoint whenever practical.

5. Validate output.
   - Run `scripts/validate_pptx.py <file.pptx>` after generating a file.
   - When a model JSON is available, run `scripts/validate_pptx.py <file.pptx> --model <model.json>` to check required text coverage for region, VCN, subnets, gateways, and resources.
   - The validator also checks renderer layout invariants for generated decks: VCN/Route Table/Security List badge sizes, subnet containment/non-overlap, standard OCI icon size, OSN vertical span and service icon alignment, connector-label overlap, and icon label font sizing.
   - With `--model`, the validator additionally checks expected resource-to-subnet containment, OSN presence only when modeled, and public/private subnet gateway combinations.
   - Check that the PPTX package is valid, has PowerPoint presentation parts, and contains at least one slide.
   - Render/preview the deck when the presentation runtime is available and inspect slide layout for overlap, missing resources, and readability.
   - Treat layout-skip warnings, validator blind spots, and unsupported custom renderer patterns as failed delivery gates unless the validator is updated in the same change.
   - Review best-practice deviations and report them as notes, not hidden changes.

## Diagram Layout Rules

Use this hierarchy for the main architecture slide: Region > VCN > Subnet > Service. The rendered diagram should make this nesting visually obvious.

```text
Region
  VCN
    Edge/Public Subnet
      Public LoadBalancer, Bastion, other internet-facing entry points
    Web/Private Subnet
      Web servers
    App/Private Subnet
      WAS, application services
    Data/Private Subnet
      Database, Exadata, storage-sensitive services
```

- Draw Region as the outer boundary. Draw the VCN as the primary inner boundary.
- Render Region containers with OCI grouping colors from `references/container-style-map.json`; do not use white or transparent fill for OCI Region or OCI Parents Region boundaries.
- When the model has top-level `vcns`, draw VCNs side by side. Use one Region boundary for same-region local peering and separate Region boundaries for cross-region remote peering.
- Place subnets inside the VCN in traffic order: Edge/Public, Security/Inspection, Web/Private, App/Private, Data/Private, Management. Use a single vertical stack up to three subnets; for four or more subnets, consider a 2 x N or VCN-internal grid unless the model explicitly sets `layout.subnet_columns`.
- For four or more subnet tiers, or when vertical room is tight and horizontal room is available, use a 2 x N VCN-internal subnet layout instead of shrinking labels/icons into unreadability.
- Put the VCN icon centered on the VCN container's upper-right vertex without a text label.
- Put Route Table and Security List icons tightly against each subnet container's upper-right corner without text labels.
- Use short role-based subnet labels in the diagram: `Public`, `Private-Web`, `Private-App`, `Private-DB`, `Security`, or `Private-Mgmt`. Keep region names, CIDRs, and expanded type/tier details in model fields or notes, not in the visible subnet header.
- Put an Oracle Service Network container to the right of the VCN with the same vertical size as the VCN when Oracle public services are represented. Label the container `OSN` to avoid narrow-box line wrapping.
- Place the model's `oracle_service_network.services` or `public_services` icons vertically inside the Oracle Service Network. Do not draw Oracle Service Network services that are not present in the model.
- When OSN has many services, use a compact readable `2 x N` service icon grid and reduce internal icon/label spacing before expanding the OSN width.
- If the diagram has substantial unused left/right whitespace, render OSN even if it was not explicitly requested. Include `IAM` and `Audit` as baseline OSN services, and include `Object Storage` when a DB, MySQL HeatWave, Exadata, Autonomous Database, or other database tier is present.
- When a resource has no explicit subnet, place API Gateway, Public LoadBalancer, Bastion, and WAF in Edge/Public; Network Firewall in Security/Inspection when available; Web servers in a private Web subnet; Compute, Functions, OKE, WAS, and app services in App/Private; Database, Exadata, MySQL, MySQL HeatWave, NoSQL, Data Flow, and Database Management in Data/Private; IAM, Audit, Object Storage, Logging, Monitoring, Vault, and related public services in Oracle Service Network.
- Public Subnet must include Bastion and must not contain Web, App, DB, MySQL, Exadata, Autonomous Database, OKE, Functions, or private compute workload resources.
- When Web and App tiers are both duplicated for HA, show Public LoadBalancer -> Web Server 1/2 and Private/Internal LoadBalancer -> App Server 1/2. Prefer naming the private LoadBalancer clearly; avoid connector labels in dense diagrams.
- Keep non-badge OCI service icons at a consistent larger size; do not resize the VCN, Route Table, or Security List corner badges unless requested.
- Put each service icon label directly under the icon, centered and close to the icon, following the normal OCI Architecture Diagram Toolkit icon-label treatment.
- Place services only inside their owning subnet unless the resource is external to OCI or is a VCN-level gateway.
- Place VCN-level gateways inside the Region and adjacent to the VCN edge: IGW/NAT/DRG on the left side when shown, Service Gateway on the boundary between VCN and OSN when shown.
- Place IGW near the public/edge subnet. Place NAT Gateway near the topmost private subnet instead of directly beside IGW.
- For local VCN peering, place `LPG` gateways on facing VCN edges near the private App tier when possible, and connect them with a no-arrow circuit line. For remote VCN peering, place `RPG` gateways with the same rule and keep them visually separated from DB/Data Guard lines.
- Put the external `User` actor outside the Region boundary and always render it with the `user` icon. Do not label it `Internet Users`. Place On-Prem, CPE, and Customer Data Center endpoints outside the Region only when requested.
- For on-premises hybrid connectivity, place On-Prem, Customer Data Center, and CPE icons inside an external network container to the left of the OCI Region. The container should use the same visual family as the OCI Region boundary.
- For hybrid/on-premises diagrams, center the combined visual group, including the external network container, CPE-to-DRG lines, OCI Region, VCN, and OSN. Do not center only the OCI Region while leaving the whole diagram left-heavy.
- In hybrid/on-premises diagrams, place the `User` icon and label near the external network container, typically centered above it with clear vertical spacing. Do not leave the User icon isolated at the far-left slide edge or overlapping the external network boundary.
- Keep gateway labels short (`IGW`, `NAT`, `DRG`, `SGW`) when space is tight, and expand the meaning in slide notes.
- For hybrid/on-premises diagrams, place the DRG in the left gateway corridor between the OCI Region boundary and the VCN, close to but not overlapping the VCN. Keep the `DRG` label directly under the icon and inside the Region boundary.
- For FastConnect and Site-to-Site VPN, use separate CPE-to-DRG relationship lines and put only the transparent `FastConnect`/`VPN` text labels on or immediately above the lines. Do not add FastConnect/VPN icons or white label canvases. Keep dual paths staggered, use dashed line treatment for VPN/backup paths, and never place a FastConnect gateway icon on top of the DRG icon.
- When a hybrid network needs more line visibility, compact the OCI side first: reduce Region/VCN/OSN horizontal footprint and use compact subnet resource grids such as `3 x 2` or `2 x 3` for dense resources. Apply this space-saving behavior only for hybrid/on-premises connectivity layouts.
- Shrink-wrap the OCI Region around the actual VCN and OSN footprint in hybrid layouts, with only enough left padding for DRG/gateway labels and enough right padding for OSN readability. Avoid large empty Region space after the OSN.
- Keep arrows sparse: show only the primary ingress path, admin path through bastion, private app-to-data path, and private egress/service-access path when relevant. If these lines reduce readability, omit connection lines from the diagram slide and keep flow details in notes.
- Render only architecture relationship lines such as VCN Peering and Data Guard/DG/ADG on the architecture slide. Do not draw workload chain lines such as `User -> IGW -> LB -> Web -> App -> DB`; summarize those traffic paths in notes instead.
- When Data Guard is modeled, keep DB-to-DB `Data Guard`, `DG`, `ADG`, or `Active Data Guard` as a straight labeled connection line.
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
- Slide 4: operational and best-practice checkpoints tailored to the requested architecture, including DR runbook items when DR is in scope.

## Output Contract

When finishing a diagram task, provide:

- Path to the generated `.pptx` file.
- Short assumption list.
- Short best-practice notes or deviations.
- Validation command result.
- Preview/render status if available.

## Resources

- `assets/OCI_Icons.pptx`: local OCI Architecture Diagram Toolkit PowerPoint source.
- `assets/cover/oracle-logo.png` and `assets/cover/oci-cover-cloud.png`: cover assets extracted from `OCI_Icons.pptx` slide 1 layout for generated title slides.
- `references/oci-best-practices.md`: Oracle best-practice checklist and source URLs.
- `references/diagram-model.md`: intermediate JSON model contract.
- `references/rendering-guidelines.md`: common deck, slide, label, footer, connector, and validation rendering rules for OCI-only and multicloud architecture decks.
- `references/consistency-guidelines.md`: consistency rules for keeping the model, renderer, validator, and final deck aligned.
- `references/icon-source.md`: icon source and common icon mapping policy.
- `references/icon-aliases.json`: required icon keys, aliases, and fallback keys for extraction.
- `references/icon-map.json`: generated icon mapping from the bundled PPTX.
- `references/icon-inventory.json`: generated slide, text, picture, and candidate inventory for review.
- `references/drawio-icon-inventory.json`: generated draw.io library match and SVG extraction inventory.
- `references/container-style-map.json`: generated OCI draw.io Physical Grouping style map for Region, AD, FD, VCN, and subnet containers.
- `references/connection-line-policy.md`: connector line, elbow-routing, arrowhead, and label policy based on OCI toolkit sample slides 29 and 30.
- `references/odb-aws-guidelines.md`: Oracle Database@AWS topology and rendering rules, including AWS multi-AZ child-site placement with one OCI Parents Region container rendered using standard OCI Region styling.
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
