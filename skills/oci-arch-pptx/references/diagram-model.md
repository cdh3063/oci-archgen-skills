# Diagram Model

Use this JSON-like contract as the intermediate representation before producing a PPTX architecture deck.

```json
{
  "title": "string",
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
  "resources": [
    {
      "id": "lb-1",
      "type": "api-gateway|load-balancer|bastion|network-firewall|compute|functions|container-engine-for-kubernetes|web-server|app-server|database|exadata|object-storage|firewall|customer-data-center",
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
  "validation": {
    "best_practice_deviations": ["string"],
    "unresolved_questions": ["string"]
  }
}
```

## Defaults

- If the user says "서울리전", use `ap-seoul-1`.
- If CIDRs are absent, use `10.0.0.0/16` for the VCN and sequential `/24` CIDRs for subnets.
- If "웹, 와스 2개씩" is given, model two web servers and two WAS/application servers.
- If Web and App tiers are both duplicated, model `Public LoadBalancer -> Web backend set` and `Private/Internal LoadBalancer -> App backend set`. Avoid direct one-to-one Web-to-App node pairing unless explicitly requested.
- If "ExaDI" is given, normalize to Exadata Database on Dedicated Infrastructure.
- If internet users are implied but not named, create an external client/internet actor only for flow clarity.
- Render Internet Users with the `user` icon rather than a cloud shape.
- If a resource has an explicit `subnet`, that subnet assignment wins.
- If `subnet` is absent, use `placement` when available, then infer placement from service `type`, `icon_key`, and `label`.
- Draw Oracle Service Network only when `oracle_service_network.services`, `public_services`, or OSN-placement resources are present in the model. Use `OSN` as the visible container label to avoid awkward wrapping in narrow side containers.
- Use `external_networks` or `on_premises` for customer data centers, CPE, partner networks, and other non-OCI endpoints.
- Use `connections` for FastConnect, VPN, and other network circuits. These are rendered as connection lines rather than workload traffic arrows unless `arrow` is explicitly true.

## PPTX Layout Contract

- Top-level containers: Region, then VCN, then subnet containers.
- If `region.availability_domains` is present, draw an Availability Domain container inside the Region and place the VCN inside it.
- Public/DMZ subnet should appear before private tiers in the traffic direction. Security/inspection subnets should appear after Edge/Public and before App/Private.
- For up to four subnets, render a single vertical stack. For five or more subnets, render a VCN-internal grid unless `layout.subnet_columns` is set.
- Default resource placement is: API Gateway, LoadBalancer, Bastion, and WAF in Edge/Public; Network Firewall in Security/Inspection when present; Compute, Functions, OKE, and app services in App/Private; Database, Exadata, MySQL, NoSQL, Data Flow, and Database Management in Data/Private; IAM, Audit, Object Storage, Logging, Monitoring, Vault, and related public services in Oracle Service Network; customer data centers and CPE outside the Region.
- For redundant Web/App tiers, place the public LoadBalancer in the public/edge subnet, place the private/internal LoadBalancer in the private App tier, connect Web servers to the private LoadBalancer, and connect the private LoadBalancer to App servers as the backend set.
- Place user/internet actors outside the OCI region boundary.
- Place gateways near the VCN edge. IGW/NAT/DRG/FastConnect-adjacent symbols are placed on the left side; Service Gateway is placed between the VCN and OSN when OSN is shown.
- Place On-Prem/Customer Data Center/CPE outside the Region and connect it to DRG with a `connections` entry such as FastConnect or VPN.
- Public/edge subnets require an Internet Gateway. Private subnets should have NAT Gateway and/or Service Gateway when private egress or OCI public service access is modeled. OSN services require a Service Gateway.
- Keep flow arrows sparse; show primary request flow and administration flow separately.
- Use orthogonal elbow connectors with staggered offsets when multiple horizontal connector lines would overlap in the same corridor.
- Use notes for security assumptions instead of overloading arrows with long text.
- Default deck: title slide, architecture diagram slide, assumptions/best-practice notes slide.
- Keep the architecture diagram slide full-page and editable: containers, icons, labels, arrows, and notes should remain PowerPoint objects when practical.
