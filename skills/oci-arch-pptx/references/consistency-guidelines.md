# OCI PPTX Consistency Guidelines

Use these rules before creating, modifying, or reviewing an OCI architecture PPTX. They prevent the model, renderer, validator, and final deck from drifting into different interpretations of the same architecture.

## Non-Negotiable Contract

- The same architecture contract must drive all artifacts: model JSON, rendered PPTX, slide notes, validation fixtures, and final response.
- Do not create a custom renderer path that bypasses the standard model contract unless the model contract and validator are updated in the same change.
- Treat any validator warning that skips layout checks as a failed delivery gate. `layout checks skipped`, missing VCN boundary checks, or missing rendered preview QA cannot be accepted as success.
- If the generated diagram uses naming, topology, or containment patterns that the validator cannot understand, update the validator or change the diagram before delivery.

## Model Consistency

- Use one canonical topology representation. Do not mix a top-level `regions` list with a single aggregated `vcn` that contains resources from multiple regions.
- For one VCN, use the standard `region -> vcn -> subnets -> resources` contract.
- For multiple VCNs, use top-level `vcns`, each with its own region, CIDR, subnets, gateways, resources, and connections.
- For cross-region DR, model each region separately and show DRG/RPG or remote peering between the regions. For same-region VCN peering, model LPG between VCNs.
- Every resource must have exactly one owning placement: subnet, OSN, VCN-level gateway, or external network.
- If a DR design omits RTO/RPO, failover mechanism, Data Guard protection mode, DNS/GSLB/Traffic Management, or automation scope, record it as an unresolved question and, when it materially affects the architecture, as a best-practice deviation or explicit assumption.

## Naming Consistency

- Shape names, model IDs, validator selectors, and slide labels must be deterministic and semantically aligned.
- Single-topology container names should keep the validator-recognized names: `Region boundary`, `VCN boundary`, `Subnet <n>`, `Oracle Service Network boundary`.
- Multi-region or multi-VCN names must follow a stable suffix pattern, such as `Region boundary:<region_id>`, `VCN boundary:<vcn_id>`, and `Subnet boundary:<subnet_id>`. The validator must understand that pattern before the deck is delivered.
- Do not rely on visible text alone for validation. The PPTX object names must also express the architecture role.
- Use one abbreviation system per deck. If labels use `P` and `S`, define them in the legend and do not mix them with unrelated `Primary`/`Standby` shorthand inside the diagram.

## Layout Consistency

- The main diagram must make containment visually obvious: Region > VCN > Subnet > Service.
- In multi-region DR, each region must have its own visible Region boundary and VCN boundary. Do not make a single logical VCN model stand in for two rendered VCNs.
- Place subnets in traffic order inside each VCN: Public/Edge, Security/Inspection when present, App/Private, Data/Private, Management.
- Place VCN-level gateways adjacent to the VCN they belong to. Do not place gateway icons so far outside the owning region or VCN that ownership is ambiguous.
- Put service gateways and OSN only when Oracle public services are modeled. If Object Storage backup, DB backup, patching, or private Oracle service access is shown or mentioned, either show SGW/OSN or state why it is outside scope.
- Keep failover controls attached to the thing that performs failover. A floating `DR Failover` box is not enough; show DNS, Traffic Management, GSLB, runbook automation, or clearly mark the mechanism as out of scope.

## Connector Consistency

- Read `references/connection-line-policy.md` before drawing connector lines.
- Workload traffic must be arrows. Network circuits such as FastConnect, VPN, LPG, RPG, DRG peering, and Data Guard must be connector lines without arrowheads unless directionality is explicitly needed.
- Use PowerPoint connector geometry and attach connectors to source and target shapes whenever possible. Do not draw important relationships as detached coordinate-only line segments.
- If endpoint attachment is technically impossible because an endpoint is a raster icon, add a named invisible anchor shape or document the fallback and verify the rendered line touches the intended object cleanly.
- Do not overload dense diagrams with protocol labels. Put protocol, port, and NSG details in notes unless the label improves readability.

## Best-Practice Consistency

- Private application and database resources must stay in private subnets unless the user explicitly requests a nonrecommended design.
- Public subnets are only for internet-facing entry points such as public load balancers and bastion access.
- Redundant Web/App tiers must use Public Load Balancer -> Web backend set and Private/Internal Load Balancer -> App backend set unless the user explicitly asks for direct node pairing.
- DR diagrams must show or explicitly defer health checks, failover trigger/control plane, replication mechanism, and standby activation behavior.
- Security notes must cover at least LB-to-backend, bastion-to-private-target, app-to-database, private egress, and inter-region replication or peering.

## Validation Gate

Run all relevant checks before delivery:

```bash
python3 scripts/validate_pptx.py <deck.pptx>
python3 scripts/validate_pptx.py <deck.pptx> --model <model.json>
```

- Both commands must pass without layout-skip warnings.
- Render every slide to PNG when the presentation runtime is available.
- Inspect the architecture slide at full size for missing containment, ambiguous ownership, label collisions, connector attachment, and unreadable icons.
- If a custom renderer is used, add or update a validation fixture that proves the validator understands the custom topology.
- The final response must report the validation commands, preview/render status, assumptions, unresolved questions, and best-practice deviations.
