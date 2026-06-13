# Connection Line Policy

Use this policy when rendering or reviewing OCI architecture connector lines. It is based on the OCI toolkit samples in `assets/OCI_Icons.pptx` slides 29 and 30.

## Visual Style

- Use dark OCI connector color `#312D2A` at `1.0 pt`.
- Use connector lines for architecture relationships only, such as Local/Remote Peering, ODB Peering, ODB Network-to-AWS Data Center / OCI Child Site relationships, Data Guard, DG, ADG, and Active Data Guard.
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

## Labels

- Keep labels short: protocol, purpose, or backend-set role, such as `HTTPS 443`, `App backend set`, `Data Guard`, or `Backup`.
- Render connector labels at 11 pt when shown.
- Omit connector labels by default on dense architecture diagrams. Put protocol, port, and security-rule details in notes instead.
- Render labels only when they clearly improve readability and have enough whitespace.
- When labels are used, render them as transparent/no-fill independent text boxes near the connector, not directly on top of the line.
- When multiple lines share the same source and label, or the same target and label, draw the label once for the group rather than repeating it on every branch.
- Place labels near the longest horizontal segment of an elbow route, away from vertical turn segments.
