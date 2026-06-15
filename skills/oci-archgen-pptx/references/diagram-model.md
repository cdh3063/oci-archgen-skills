# Diagram Model

Use this JSON-like contract as the intermediate representation before producing a PPTX architecture deck.

```json
{
  "title": "English architecture title",
  "language": "ko|en",
  "region": {
    "name": "Seoul",
    "oci_region": "ap-seoul-1",
    "availability_domains": ["AD 1"]
  },
  "assumptions": ["string"],
  "architecture_notes": ["string"],
  "layout": {
    "subnet_columns": "number|null"
  },
  "external_networks": [
    {
      "id": "on-prem",
      "type": "customer-data-center|customer-premises-equipment|on-premises",
      "label": "On-Prem Data Center",
      "icon_key": "customer-data-center"
    }
  ],
  "on_premises": {
    "id": "on-prem",
    "label": "On-Prem",
    "type": "customer-data-center"
  },
  "oracle_service_network": {
    "enabled": true,
    "services": [
      {
        "id": "object-storage",
        "type": "object-storage",
        "label": "Object Storage",
        "icon_key": "object-storage"
      }
    ]
  },
  "public_services": ["IAM", "Audit", "Object Storage"],
  "vcn": {
    "name": "VCN",
    "cidr": "10.0.0.0/16",
    "subnets": [
      {
        "name": "Public",
        "type": "public|private",
        "tier": "dmz|app|db|management",
        "cidr": "10.0.0.0/24",
        "resources": ["resource-id"]
      }
    ],
    "gateways": [
      {
        "id": "igw-1",
        "type": "internet-gateway|nat-gateway|service-gateway|drg|dynamic-routing-gateway|local-peering-gateway|fastconnect|customer-premises-equipment",
        "label": "Internet Gateway"
      }
    ]
  },
  "vcns": [
    {
      "name": "Primary VCN",
      "cidr": "10.10.0.0/16",
      "region": {
        "name": "Seoul",
        "oci_region": "ap-seoul-1"
      },
      "subnets": [],
      "gateways": [
        {
          "id": "primary-rpg",
          "type": "remote-peering-gateway|remote-peering-connection|local-peering-gateway",
          "label": "Remote Peering Gateway"
        }
      ]
    }
  ],
  "resources": [
    {
      "id": "lb-1",
      "type": "api-gateway|load-balancer|bastion|network-firewall|compute|functions|container-engine-for-kubernetes|web-server|app-server|database|mysql|exadata|object-storage|firewall|customer-data-center",
      "label": "LoadBalancer",
      "subnet": "Public",
      "placement": "edge|security|app|data|management|osn|external",
      "count": 1,
      "ha_group": "string|null",
      "icon_key": "load-balancer",
      "notes": ["string"]
    }
  ],
  "flows": [
    {
      "from": "internet",
      "to": "lb-1",
      "label": "HTTPS 443",
      "security": "Allow from required source CIDR"
    }
  ],
  "connections": [
    {
      "id": "fc-1",
      "type": "fastconnect|vpn|connection",
      "from": "on-prem",
      "to": "drg-1",
      "label": "FastConnect",
      "arrow": false
    }
  ],
  "operational_advice": {
    "resilience": ["string"],
    "security": ["string"],
    "operations": ["string"],
    "cost": ["string"],
    "open": ["string"]
  },
  "validation": {
    "best_practice_deviations": ["string"],
    "unresolved_questions": ["string"]
  }
}
```

## Defaults

- `language` tracks the user's input/narrative language for slides 3 and 4. It does not localize architecture-facing labels.
- Keep architecture-facing strings in English even for Korean input: `title`, `subtitle`, VCN names, subnet names, resource labels, gateway labels, connector labels, OSN service labels, AWS/OCI container labels, and diagram titles.
- Use the input language for narrative fields such as `assumptions`, `architecture_notes`, `operational_advice`, `validation.best_practice_deviations`, and `validation.unresolved_questions`.
- If the user says "서울리전", use `ap-seoul-1`.
- If CIDRs are absent, use `10.0.0.0/16` for the VCN and sequential `/24` CIDRs for subnets.
- Use concise role-based subnet names by default. Prefer `Public`, `Private-Web`, `Private-App`, `Private-DB`, `Security`, or `Private-Mgmt`; do not create visible names that combine region, access type, and tier such as `Seoul Private App`.
- If "웹, 와스 2개씩" is given, model two web servers and two WAS/application servers.
- If Web and App tiers are both duplicated, model Public Subnet with Public LoadBalancer and Bastion, private Web subnet with Web servers, and private App subnet with Private/Internal LoadBalancer and App servers. Avoid direct one-to-one Web-to-App node pairing unless explicitly requested.
- Public Subnet is only for public entry and administration controls such as Public LoadBalancer, WAF/API Gateway when requested, and Bastion. Always include Bastion in Public Subnet.
- Never place Web, App, DB, MySQL, MySQL HeatWave, Exadata, Autonomous Database, OKE, Functions, or private compute workload resources in Public Subnet. If the user asks for a public web/app/db tier, treat it as a best-practice deviation and keep the recommended diagram private unless they explicitly require the deviation.
- If the diagram has substantial unused left/right whitespace, include OSN in the model. OSN baseline services are `IAM` and `Audit`; if any DB, MySQL HeatWave, Exadata, Autonomous Database, or database tier is present, also include `Object Storage`.
- When OSN is included, add `service-gateway` to `vcn.gateways` and label it `Service Gateway`.
- If two or more VCNs are modeled, use top-level `vcns` instead of `vcn`; each VCN entry uses the same `subnets` and `gateways` schema as `vcn`.
- If two VCNs are in the same OCI region, model local peering with `local-peering-gateway` endpoints and an `LPG` connection.
- If two VCNs are in different OCI regions, model remote peering with `remote-peering-gateway` or `remote-peering-connection` endpoints and an `RPG` connection.
- If "ExaDI" is given, normalize to Exadata Database on Dedicated Infrastructure.
- Always render the external actor with the `user` icon labeled `User`; do not use `Internet Users`.
- Do not add optional OSN services such as Logging, Monitoring, Object Storage, Vault, or Audit unless the user requested them or the architecture explicitly depends on them.
- Do not add `flows` for architecture-slide rendering. Put workload paths such as `User -> IGW -> LB -> Web -> App -> DB` in notes instead of drawing them.
- Use `connections` only for architecture relationship lines such as Local/Remote Peering, ODB Peering, Data Guard, DG, ADG, and Active Data Guard unless the user explicitly asks for another relationship line.
- If a resource has an explicit `subnet`, that subnet assignment wins.
- If `subnet` is absent, use `placement` when available, then infer placement from service `type`, `icon_key`, and `label`.
- Draw Oracle Service Network only when `oracle_service_network.services`, `public_services`, or OSN-placement resources are present in the model. Use `OSN` as the visible container label to avoid awkward wrapping in narrow side containers.
- When OSN includes five or more services, render OSN services in a compact readable `2 x N` grid rather than a cramped single column. Reduce internal OSN icon spacing and padding before increasing OSN width.
- For whitespace-driven OSN placement, model the OSN services explicitly as `IAM`, `Audit`, and optionally `Object Storage` for DB architectures.
- Use `external_networks` or `on_premises` for customer data centers, CPE, partner networks, and other non-OCI endpoints.
- When `external_networks`, `on_premises`, FastConnect, or Site-to-Site VPN is modeled, expect a left-side external network container rendered with the OCI Region container style. Place On-Prem/CPE icons inside that container rather than as loose icons.
- Use `connections` for Peering and Data Guard/DG/ADG relationship lines. Do not model ordinary workload request chains as slide connectors.
- Use `connections` for hybrid network relationships such as FastConnect and Site-to-Site VPN. FastConnect may appear in `vcn.gateways` for text coverage, but it should render as a labeled CPE/on-premises-to-DRG relationship line, not as a VCN gateway icon overlapping DRG.
- In hybrid/on-premises layouts, compact the OCI Region/VCN/OSN footprint when needed to preserve CPE-to-DRG line visibility. For dense peer resources in a subnet, prefer compact grids such as `3 x 2` or `2 x 3`. Apply this only to hybrid layouts, not ordinary OCI-only diagrams.
- In hybrid/on-premises layouts, center the combined visual group across the slide, including external network, CPE-to-DRG lines, OCI Region, VCN, and OSN. The OCI Region should be shrink-wrapped around the VCN and OSN footprint instead of keeping broad unused space after OSN.

## PPTX Layout Contract

- Apply `references/rendering-guidelines.md` for common deck structure, title slide, diagram title, footer disclaimer, label alignment, connector readability, notes, checkpoints, and render/preview validation rules.
- Top-level containers: Region, then VCN, then subnet containers.
- For top-level `vcns`, draw VCNs side by side. Use one Region container when their region is the same, and separate Region containers when their `region.oci_region` values differ.
- For local peering, place `LPG` gateways on the facing VCN edges and connect them with a circuit line. For remote peering, place `RPG` gateways on the facing VCN edges and connect them with a circuit line.
- If `region.availability_domains` is present, draw an Availability Domain container inside the Region and place the VCN inside it.
- Public/DMZ subnet should appear before private tiers in the traffic direction. Security/inspection subnets should appear after Edge/Public and before App/Private.
- Render subnet headers using concise role names only: `Public`, `Private-Web`, `Private-App`, `Private-DB`, `Security`, or `Private-Mgmt`. Keep CIDR, region, and expanded type/tier details out of the visible subnet header.
- Render a single vertical stack by default through four subnets, including `1 x 4`. For five or more subnets, or whenever a four-subnet stack lacks usable vertical room and horizontal room is available, use a `2 x N` or VCN-internal grid layout unless `layout.subnet_columns` is set.
- Default resource placement is: API Gateway, Public LoadBalancer, Bastion, and WAF in Edge/Public; Network Firewall in Security/Inspection when present; Web servers in Web/Private; Compute, Functions, OKE, WAS, and app services in App/Private; Database, Exadata, MySQL, MySQL HeatWave, NoSQL, Data Flow, and Database Management in Data/Private; IAM, Audit, Object Storage, Logging, Monitoring, Vault, and related public services in Oracle Service Network; customer data centers and CPE outside the Region.
- For redundant Web/App tiers, place the public LoadBalancer and Bastion in the public/edge subnet, place Web servers in a private Web subnet, place the private/internal LoadBalancer in the private App tier, and place App servers behind it as the backend set.
- Place user/internet actors outside the OCI region boundary.
- Place gateways near the VCN edge. IGW/NAT/DRG/FastConnect-adjacent symbols are placed on the left side; Service Gateway is placed between the VCN and OSN when OSN is shown.
- Place IGW near the public/edge subnet. Place NAT Gateway near the topmost private subnet.
- Place LPG/RPG gateways on facing VCN edges near the private App tier when possible, keeping them visually separated from DB/Data Guard lines.
- Place On-Prem/Customer Data Center/CPE outside the Region and connect it to DRG with a `connections` entry such as FastConnect or VPN.
- For On-Prem/Customer Data Center/CPE, draw a customer network box to the left of the OCI Region using the same visual family as the Region container. Place CPE and customer data center icons inside the box and keep their labels contained and readable.
- Place the `User` icon and label near the external network container, usually centered above it, with enough vertical spacing to avoid overlap with the external network label/boundary.
- Place DRG in the left gateway corridor between the OCI Region boundary and VCN, with its label directly below it and contained inside the Region.
- For FastConnect and Site-to-Site VPN dual connectivity, draw separate relationship lines between CPE/on-premises and DRG and place only transparent `FastConnect`/`VPN` text labels on or immediately above the lines. Do not add separate FastConnect/VPN icons or white label canvases. Use no arrowhead; use dashed line treatment for VPN/backup paths when shown. Keep DRG, CPE, FastConnect/VPN labels, and line paths from overlapping each other.
- Public/edge subnets require an Internet Gateway. Private subnets should have NAT Gateway and/or Service Gateway when private egress or OCI public service access is modeled. OSN services require a Service Gateway.
- Do not draw workload flow arrows on the architecture slide. Summarize ingress, LB/backend, web/app, app/DB, and egress assumptions in notes.
- Use orthogonal elbow connectors with staggered offsets when multiple horizontal connector lines would overlap in the same corridor.
- Use notes for security assumptions instead of overloading arrows with long text.
- Render architecture component labels at 11 pt by default. Resize or reposition containers/icons instead of shrinking labels below 11 pt.
- Render all architecture labels as transparent/no-fill text boxes. Do not use opaque white fill behind labels.
- Use the standard service icon size by default, but reduce icon size when icons or labels would overflow their subnet/container. Containment and readability take priority over fixed icon size.
- Default deck: title slide, architecture diagram slide, assumptions/best-practice notes slide, operational/best-practice checkpoint slide.
- The title slide should follow the common rendering guideline for all generated decks.
- The architecture diagram slide footer should follow the common rendering guideline for AI-output verification disclaimers.
- If `operational_advice` is present, use it for the final checkpoint slide. Otherwise generate checkpoint guidance from the modeled topology, including DR-specific RTO/RPO, failover/failback, replication, DNS/GSLB, and runbook items when DR is in scope.
- Keep the architecture diagram slide full-page and editable: containers, icons, labels, arrows, and notes should remain PowerPoint objects when practical.
