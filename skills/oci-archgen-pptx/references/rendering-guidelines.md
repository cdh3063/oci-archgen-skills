# Common Rendering Guidelines

Use these rules for every generated architecture deck, including OCI-only, multi-region OCI DR, and Oracle Database@AWS diagrams. Provider-specific topology rules can differ, but slide structure, visual hierarchy, titles, disclaimers, and readability standards should stay consistent.

## Deck Structure

- Produce a concise deck by default: title slide, architecture diagram slide, assumptions/best-practice notes slide, and operational/best-practice checkpoint slide.
- Use the `assets/OCI_Icons.pptx` slide 1 title-page form for every generated deck: Oracle-branded white cover, Oracle logo placement, large architecture title, concise subtitle, and small bottom metadata.
- Do not make AWS or another non-OCI vendor logo the main cover signal, even when the diagram is multicloud or ODB@AWS.
- Keep slide titles architecture-specific, not explanatory constraint sentences. Prefer titles such as `3Tier DR Architecture`, `Remote Peering DR Architecture`, `ODB@AWS Multi AZ DR 아키텍쳐`, or `ODB@AWS Multi-AZ DR Architecture`.

## Main Diagram Slide

- The architecture diagram slide should use a full-page editable diagram area with a compact header and footer. Avoid card-style frames around the whole architecture.
- Use one visual hierarchy per diagram and make containment obvious. Examples: `Region > VCN > Subnet > Service` for OCI, or `AWS Cloud > AWS Region > Availability Zone > ODB network / AWS data center > OCI child site` for ODB@AWS.
- Center the overall diagram group on the slide so left and right page margins feel balanced.
- Keep every child container fully inside its parent boundary. If a child box is stretched for readability, expand or reposition the parent boundary so containment is still visually correct.
- Balance left and right padding inside major parent containers such as Region, AWS Region, VCN, and Availability Zone. If inner elements feel right-heavy, shift the child boundary and its contents left rather than expanding only the right edge.
- Keep child containers visibly inset from their parent boundaries; do not let Availability Zone, VCN, subnet, VPC, or ODB Network borders sit on or nearly touch the parent Region/AWS Region border. Use consistent left/right inset values so sibling boxes appear horizontally symmetric.
- Adjust top and bottom margins when needed so architecture icons and 11 pt labels have enough room. Do not keep large vertical whitespace while shrinking diagram labels or icons.
- Default subnet layout is a single-column `1 x N` vertical stack through four subnet tiers, including `1 x 4`. Use a `2 x N` subnet layout only when the single-column stack lacks usable vertical room and the parent VCN has horizontal room.
- Put explanatory constraints, caveats, and implementation notes in notes or checkpoint slides, not as large text inside the diagram body.
- Keep important relationships visible on the diagram, but move dense protocol, port, security-list, and routing details to notes unless the user explicitly requests them on the diagram.
- Do not add optional services, OSN entries, gateways, external actors, or connector lines only to make a diagram look complete. Render them only when the user requested them, the model explicitly includes them, or they are required to make the requested topology coherent. Record assumptions in notes instead of silently expanding the diagram.
- Exception: always render the external actor as a `User` icon labeled `User`; do not use `Internet Users`.
- Exception: when the overall OCI diagram has substantial unused left/right whitespace, render OSN to use that space. OSN must include `IAM` and `Audit`; if any DB tier exists, include `Object Storage` as well.
- For OCI diagrams, always keep Public Subnet limited to public entry and administration controls such as Public Load Balancer, WAF/API Gateway when requested, and Bastion. Always show Bastion in the Public Subnet.
- Never place Web, App, DB, MySQL, Exadata, Autonomous Database, OKE, Functions, or private compute workload resources in a Public Subnet. Place them in private Web/App/Data subnets even when Web and App are separated.
- When on-premises, customer data center, CPE, FastConnect, or Site-to-Site VPN connectivity is requested, render the customer network as a separate external network container to the left of the OCI Region. Use the same container treatment as the OCI Region family and label the container as `On-Prem` / `Network` on two lines. Keep concrete On-Prem server/DC, CPE, database, and other on-premises resource icons inside it, but do not render a duplicate `On-Prem Network` icon and label inside the container. If the model only declares CPE endpoints, add a small On-Prem server/DC icon for context.
- For hybrid/on-premises diagrams, preserve CPE-to-DRG connection-line visibility by compacting the OCI side before shrinking labels: reduce Region/VCN/OSN horizontal footprint and use dense subnet resource grids such as `3 x 2` or `2 x 3` when a subnet has many peer resources. Do not apply this compacting rule to ordinary OCI-only layouts.
- For hybrid/on-premises diagrams, center the whole architecture group on the slide: external network container, CPE-to-DRG connection lines, OCI Region, VCN, and OSN. The visual center should not be calculated from the OCI Region alone.
- Shrink-wrap the OCI Region around the actual VCN and OSN footprint in hybrid layouts. Leave only enough left padding for DRG/gateway placement and enough right padding for OSN readability; avoid broad empty Region space after the OSN.
- Do not add decorative logos or badges that do not clarify ownership or topology.

## Labels And Text

- Keep labels short and consistent. Use expanded terms in notes when the diagram needs compact labels such as `IGW`, `NAT`, `DRG`, `SGW`, `OSN`, `LPG`, or `RPC`.
- Keep architecture-facing labels in English for every deck, regardless of the user's input language. This includes deck title, diagram title, outer/container labels, subnet labels, resource labels, gateway labels, connector labels, and model-visible service labels.
- Use Title Case for English diagram labels and model-visible labels. For example, use `VPC Subnet`, `ODB Network`, `AWS Data Center`, `OCI Child Site`, `OCI Parents Region`, and `OCI Control Plane`.
- Center-align primary outer-container labels at the top of the container unless a provider-specific guideline says otherwise.
- When a small provider/service icon is used as a corner badge, place the icon tightly at the top-left corner and align the label next to it.
- Do not place descriptive statements such as `single-AD based view`, `only major traffic shown`, or similar caveats inside the main diagram body.
- Render architecture component labels at 11 pt by default, including container labels, subnet labels, service labels, and connector labels.
- Do not reduce architecture component labels below 11 pt to force-fit a dense layout. Instead resize or reposition containers/icons, shorten the visible label, or move details to notes.
- Keep font sizes readable and avoid text overlap. If a label cannot fit at 11 pt, shorten the label and move the detail to notes.
- Render every diagram label as a transparent/no-fill text box. Do not use a white canvas behind connector labels, service labels, gateway labels, subnet labels, or container labels.
- Keep visible OCI subnet labels short and role-based: `Public`, `Private-Web`, `Private-App`, `Private-DB`, `Security`, or `Private-Mgmt`. Do not concatenate region, subnet type, tier, and CIDR into the header; avoid labels such as `Seoul Private App - Private - APP`.
- For common long service labels, insert intentional line breaks instead of allowing PowerPoint to split words mid-token. Preferred breaks include `Public` / `Load Balancer`, `Internal` / `Load Balancer`, and `MySQL` / `HeatWave N`.
- Follow the user's input language only for narrative content on slides 3 and 4, such as assumptions, security notes, rendering notes, and operational/best-practice checkpoints. Do not localize the architecture labels on slides 1 and 2 unless the user explicitly overrides this policy.

## Diagram Footer Disclaimer

- Put the AI-output verification disclaimer in the architecture diagram slide footer.
- Korean disclaimer text: `본 문서는 AI 산출물이므로 정확하지 않을 수 있습니다. 반드시 검증 후 사용하십시오.`
- English disclaimer text: `This document was generated by AI and may be inaccurate. Validate thoroughly before use.`
- Style the disclaimer as 10 pt red text, left-aligned, near the lower-left edge of the architecture diagram slide.
- Do not replace the disclaimer with flow-readability explanations. Put readability explanations in notes if needed.

## Icons And Containers

- Use OCI Architecture Diagram Toolkit assets for OCI services and containers whenever available.
- Use provider-specific assets only for provider-specific resources. For example, AWS icons may be used for VPC, Transit Gateway, EC2, ODB@AWS, or AWS data center elements, but the deck cover remains OCI/Oracle branded.
- For ODB@AWS diagrams, AWS-side provider icons and network containers must follow `references/odb-aws-guidelines.md` and use registered `assets/odb-aws/` assets extracted from the reference `odb-aws-architecture.pptx`; do not invent fallback AWS/ODB icons.
- Keep service icons consistently sized within the same tier or grouping.
- Use the standard service icon size by default, but reduce icon size when resource density would push icons, labels, or boundaries outside their owning container. Keep icons readable and preserve containment over strict size uniformity.
- Center a single service icon within its owning container when it represents the main workload in that container.
- Place the service label directly under the icon, centered and close to the icon, following the OCI Architecture Diagram Toolkit icon-label treatment.
- Use icons as ownership or service signals, not decoration. Remove icons that make a container header crowded or redundant.
- Keep containers, icons, labels, arrows, and notes editable in PowerPoint whenever practical.

## OSN Placement

- Place OSN to the right of the VCN when there is enough horizontal room and it does not make the main topology cramped.
- Use compact labels: `IAM`, `Audit`, and `Object Storage`.
- When OSN has five or more services, first reduce icon spacing and internal padding, then use a compact readable `2 x N` grid. Widen the OSN only as much as needed for labels. Use intentional line breaks for long labels such as `Object Storage`, `Cloud Guard`, and `Vulnerability Scanning`.
- If OSN is rendered, include a Service Gateway between the VCN and OSN.
- If a database tier is present, include `Object Storage` for backup/export/private service access context unless the user explicitly says not to show storage services.

## OCI Container Color

- Render OCI Region and OCI Parents Region containers with OCI grouping colors from `container-style-map.json`; do not use white or transparent fill for OCI Region boundaries.
- OCI Parents Region in ODB@AWS diagrams must visually match the OCI Region family, using a gray OCI grouping fill and `#9E9892` line color.
- This OCI Parents Region rule is an explicit ODB@AWS exception: AWS Cloud, AWS Region, AZ, VPC Subnet, ODB Network, AWS Data Center, OCI Child Site, and OCI VCN containers follow the ODB@AWS reference PPTX AWS architecture styling instead.
- If the standard light OCI Region fill has insufficient contrast against the slide background, use a stronger OCI grouping gray from the same OCI container palette rather than leaving the region visually white.

## Connectors

- Use connector lines only for architecture relationship lines such as VCN Peering, ODB Peering, Data Guard, DG, ADG, and Active Data Guard. Do not draw workload traffic chains such as `User -> IGW -> LB -> Web -> App -> DB`; describe those paths in notes.
- Treat FastConnect and Site-to-Site VPN as hybrid network relationship lines. Show CPE/on-premises and DRG as endpoint icons, draw separate CPE-to-DRG lines, and place only transparent `FastConnect`/`VPN` text labels on or immediately above the lines. Do not render separate FastConnect/VPN icons and do not render FastConnect as a VCN-side gateway icon overlapping DRG.
- For OCI CLI/resource inventory diagrams with explicit IPSec VPN resources, render one relationship per VPN resource. If two CPEs connect to one DRG, stack the CPE icons vertically and place the DRG centered between them so the VPN lines converge in a `>` shape. Place the registered `site-to-site-vpn` marker at the DRG-side endpoint of each VPN line, not in the line center, including the single-VPN case. The OCI draw.io library has `Physical - Special Connectors - Site-to-site-VPN - Vertical` as a reference connector; use the registered extracted marker asset when available and fall back to an editable lock marker only if the asset is missing.
- In hybrid layouts, place the DRG in the left gateway corridor between the OCI Region boundary and the VCN. Keep it close to the VCN without overlapping the VCN boundary, and keep the `DRG` label directly under the icon inside the Region.
- Place the `User` icon and label near the external network container, usually centered above it with clear spacing from the container label. Do not leave it isolated on the far-left slide margin.
- Keep connector labels close to the relevant line and centered on the line when practical.
- Render connector labels at 11 pt when they are shown.
- For hub icons such as Transit Gateway, align the hub center with the connected container centers when the intended connection is vertical or horizontal.
- For same-region Local Peering, use DRG icon assets at both peering endpoints, label those endpoint icons `LPG`, and place a transparent `Local Peering` label on or immediately above the connector line.
- For cross-region Remote Peering, use DRG icon assets at both peering endpoints, label those icons `DRG` only, and place a transparent `RPC` label on or immediately above the connector line. Do not use `RPG` as a visible icon label.
- Separate visually similar relationships, such as VCN peering and Data Guard, so they do not overlap or imply the wrong dependency.
- Prefer orthogonal or staggered connector routing when multiple horizontal or vertical lines would collide.
- Avoid connector labels in dense diagrams unless the label improves understanding.

## Notes And Checkpoints

- Every generated deck should include notes that capture assumptions, unresolved questions, substitutions, and best-practice deviations.
- Every generated deck should include a final operational/best-practice checkpoint slide tailored to the requested architecture.
- For DR architectures, include RTO/RPO, replication mode, failover/failback ownership, DNS/GSLB or traffic cutover, monitoring, and drill/runbook checkpoints.
- For non-DR architectures, include security, monitoring, backup/restore, capacity, cost, runbook, and ownership checkpoints tailored to the modeled services.

## Validation

- Run the PPTX validator after generation and use model-aware validation when a model JSON is available.
- Render every generated deck to PNG when the presentation runtime is available.
- Inspect the architecture slide for missing containment, ambiguous ownership, label collisions, connector overlap, unreadable icons, and footer disclaimer placement.
- If a custom topology uses a renderer or shape naming pattern that the validator cannot understand, update the validator or add a validation fixture before treating the deck as complete.
