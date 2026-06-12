# OCI Best-Practice Checklist

Checked against Oracle public documentation on 2026-06-05.

## Sources

- OCI Well-Architected Framework: https://docs.oracle.com/en/solutions/oci-best-practices/index.html
- Oracle Cloud Architecture Center: https://www.oracle.com/cloud/architecture-center/
- Securing Networking: VCN, Load Balancers, and DNS: https://docs.oracle.com/en-us/iaas/Content/Security/Reference/networking_security.htm
- High Availability: https://docs.oracle.com/en-us/iaas/Content/cloud-adoption-framework/high-availability.htm
- Extreme Reliability: https://docs.oracle.com/en-us/iaas/Content/cloud-adoption-framework/extreme-reliability.htm
- Shared Responsibility Model for Resiliency: https://docs.oracle.com/en-us/iaas/Content/cloud-adoption-framework/oci-shared-responsibility.htm
- OCI Architecture Diagram Toolkits: https://docs.oracle.com/en-us/iaas/Content/General/Reference/graphicsfordiagrams.htm

## Diagram Rules

- Anchor recommendations to the five OCI Well-Architected pillars: security and compliance, reliability and resilience, performance and cost optimization, operational efficiency, and distributed cloud.
- Use regional subnets by default. Show AD-specific placement only when the user asks for it or when HA placement matters to the diagram.
- Use tiered network segmentation:
  - DMZ/public subnet for internet-facing load balancers, WAF/API Gateway when requested, and bastion access.
  - Private web subnet for web servers when a Web tier is modeled.
  - Private application subnet for WAS, middleware, APIs, and internal compute.
  - Private database subnet for DB systems, Exadata, Autonomous Database private endpoints, and storage-sensitive components.
- Always include Bastion in Public Subnet for OCI architecture diagrams.
- Do not place Web, App, DB, MySQL, MySQL HeatWave, Exadata, Autonomous Database, OKE, Functions, or private compute workloads in Public Subnet. If the user explicitly requests this nonrecommended design, flag it as a deviation and still present the recommended private placement unless they insist on the deviation.
- Do not place database resources in public subnets unless the user explicitly requests a nonrecommended design; flag it as a deviation.
- Show private subnet resources with private IP-only access.
- Add NSG or security-list annotations when the diagram includes traffic flows:
  - Internet to public load balancer: HTTPS/TLS.
  - Load balancer to web/app backends: allow only from load balancer NSG/subnet.
  - Bastion to private targets: allow SSH/RDP only from authorized CIDR through bastion.
  - App to DB: allow only required database ports from app tier.
- Show egress patterns when relevant:
  - Internet gateway for public subnet ingress/egress.
  - NAT gateway for private outbound internet access without inbound exposure.
  - Service gateway for private access to Oracle services such as Object Storage backups.
  - DRG/FastConnect/VPN for private on-premises or inter-region connectivity.
- When the diagram has substantial unused left/right whitespace, show OSN rather than leaving the slide sparse. Include IAM and Audit as baseline services. If a DB tier is present, include Object Storage for backup/export/private Oracle service access context.
- For public load balancers, prefer a regional public/DMZ subnet and HA placement across availability domains where the region supports it.
- For HA, represent redundancy explicitly:
  - Minimum two web/application nodes when the user asks for HA or gives two instances.
  - When both Web and App tiers are redundant, show Public Load Balancer -> Web backend set and Private/Internal Load Balancer -> App backend set.
  - Spread redundant compute across fault domains, and across availability domains when required and available.
  - Include health checks and failover notes when showing load balancers.
- For Exadata Database on Dedicated Infrastructure or Exadata Cloud Service, show it in the private DB tier and note MAA/RAC/Data Guard options when HA or DR is in scope.
- For mission-critical DR, replicate the stack across regions and show asynchronous replication mechanisms only when DR is requested.

## Review Flags

- Public IP on DB or private app nodes.
- Web/App/DB resources placed in Public Subnet.
- Public Subnet without Bastion.
- Internet gateway route attached to private DB subnet.
- Open SSH/RDP from `0.0.0.0/0`.
- Backends accepting traffic from the internet instead of only from the load balancer.
- Single compute instance for a tier that the user described as highly available.
- Redundant App servers shown behind direct Web-to-App node pairing instead of a private/internal load balancer backend set.
- No fault-domain or AD spread for redundant nodes in a diagram that claims HA.
- No service gateway/NAT path for private backups or patching when those flows are shown.
