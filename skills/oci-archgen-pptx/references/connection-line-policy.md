# Connection Line Policy

Use this policy when rendering or reviewing OCI architecture connector lines. It is based on the OCI toolkit samples in `assets/OCI_Icons.pptx` slides 29 and 30.

## Visual Style

- Use dark OCI connector color `#312D2A` at `1.0 pt`.
- Use connector lines for architecture relationships only, such as Local Peering, RPC, ODB Peering, ODB Network-to-AWS Data Center / OCI Child Site relationships, Data Guard, DG, ADG, Active Data Guard, FastConnect, and Site-to-Site VPN.
- Do not draw ordinary workload request chains such as `User -> IGW -> LB -> Web -> App -> DB`; put those traffic assumptions in notes.
- Use no arrowhead for Peering and Data Guard relationship lines unless directionality is explicitly required.
- Use dashed lines only for administrative, SSH/RDP, VPN, or explicitly non-primary paths.
- Use PowerPoint connector geometry (`straightConnector1`) rather than freeform line geometry.

## Routing

- Keep short, single-hop, non-overlapping relationship links straight.
- Use orthogonal elbow routing for long cross-tier links, links that cross container boundaries, and any horizontal corridor where multiple lines would overlap.
- For fan-out and fan-in patterns, use staggered offsets so parallel horizontal segments do not sit on top of each other.
- Keep connector paths outside icon centers and away from subnet/container labels where practical.
- Put the final arrowhead only on the last segment of an orthogonal route.
- If routing still reduces readability after simplification, omit optional relationship lines from the architecture slide and move details to notes.
- When Data Guard is modeled, draw the DB-to-DB `Data Guard`, `DG`, `ADG`, or `Active Data Guard` relationship as a straight labeled connection line.
- When Local Peering is modeled, draw a no-arrow line between LPG endpoints and label the line `Local Peering`. LPG endpoints use the DRG icon asset with visible label `LPG`.
- When Remote Peering is modeled, draw a no-arrow line between DRG icons and label the line `RPC`. Remote peering uses the DRG icon asset with visible label `DRG` only; do not render an `RPG` icon label.
- When FastConnect or Site-to-Site VPN is modeled, draw the relationship between CPE/on-premises and DRG. Use the connector line itself with a transparent `FastConnect` or `VPN` text label on or immediately above the line. Do not add separate FastConnect/VPN icons. Keep FastConnect solid by default, use dashed treatment for VPN/backup paths, and stagger dual paths so the lines and labels do not overlap.
- Exception for OCI CLI/resource inventory diagrams: when explicit IPSec VPN resources are present, render each VPN as a separate CPE-to-DRG relationship with the registered `site-to-site-vpn` marker at the DRG-side endpoint, not in the line center. If two CPEs connect to one DRG, stack the CPEs vertically and route both VPN lines to the centered DRG as a `>` convergence. Keep an On-Prem server/DC icon inside the external network container even when the model only declares CPE endpoints. The draw.io source includes `Physical - Special Connectors - Site-to-site-VPN - Vertical` as the visual reference; use the registered extracted marker asset when available and fall back to an editable lock marker only if the asset is missing.
- Do not render FastConnect as a gateway icon directly on top of DRG. If the model includes a FastConnect gateway entry, treat it as a connection label source.
- For hybrid CPE-to-DRG layouts, place DRG in the left gateway corridor between the OCI Region boundary and VCN. Center the combined external-network, connection-line, Region, VCN, and OSN group on the slide rather than centering the OCI Region alone.

## Labels

- Keep labels short: protocol, purpose, or backend-set role, such as `HTTPS 443`, `App backend set`, `Data Guard`, or `Backup`.
- Render connector labels at 11 pt when shown.
- Omit connector labels by default on dense architecture diagrams. Put protocol, port, and security-rule details in notes instead.
- Render labels only when they clearly improve readability and have enough whitespace.
- When labels are used, render them as transparent/no-fill independent text boxes near the connector. Do not use white fill, white backing rectangles, or any opaque label canvas.
- When multiple lines share the same source and label, or the same target and label, draw the label once for the group rather than repeating it on every branch.
- Place labels near the longest horizontal segment of an elbow route, away from vertical turn segments.
- For short CPE-to-DRG hybrid paths, keep the line label close to the line and validate it does not collide with DRG, IGW, CPE, subnet, or resource labels.
