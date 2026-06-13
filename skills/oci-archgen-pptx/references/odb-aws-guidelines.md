# Oracle Database@AWS Guidelines

Use these rules when a request mentions Oracle Database@AWS, ODB@AWS, OD@AWS, or Oracle Database at AWS.

Apply `references/rendering-guidelines.md` first for common slide structure, title slide, diagram title, footer disclaimer, label alignment, connector readability, notes, checkpoints, and validation rules. This file only adds Oracle Database@AWS-specific topology and placement rules.

## Topology

- Model Oracle Database@AWS as a multicloud topology, not as a normal OCI-only VCN layout.
- Use one AWS Cloud boundary containing one AWS Region boundary.
- Within one AWS Region, show one or more AWS Availability Zones as needed.
- AWS placement is multi-AZ capable: if ODB@AWS is deployed in Availability Zone a and b, render separate AZ-level ODB/OCI child-site placements inside the same AWS Region.
- OCI Parents Region placement is represented as one OCI Parents Region container for this diagram pattern: even when one AWS Region has ODB@AWS deployed in multiple AZs, render exactly one OCI Parents Region container.
- Each AWS AZ placement can contain its own ODB network and OCI child site. The ODB network is AZ-specific.
- The Amazon VPC can span multiple AZs; application resources such as EC2 should be placed in the VPC/AZ area that owns their traffic path.
- Show ODB peering between the Amazon VPC and ODB network. Treat ODB peering as distinct from VPC peering.
- Do not use a generic Amazon VPC Peering icon as the primary ODB Peering symbol. The AWS Oracle Database@AWS guide describes ODB Peering as distinct from VPC Peering, so render ODB Peering with `assets/odb-aws/odb-peering-marker.png`, the purple circular ODB peering marker extracted from the guide image. Keep the marker centered on the ODB peering line with the label aligned close to the line.
- When a directional arrow is shown between the OCI child-site VCN and the ODB network, point the arrow from the OCI child-site VCN toward the ODB network.
- When multiple VPCs or multiple VPC/AZ placements need to be connected, show AWS Transit Gateway as the inter-VPC hub when requested. Place the Transit Gateway relationship between the VPC placements and keep its label aligned to the connector.
- Show the OCI child site inside the AWS data center/AZ area. Inside the child site, show the OCI VCN, client subnet, backup subnet when relevant, and Exadata databases or VM cluster.
- When two Exadata database icons represent replicated database endpoints, label the relationship as Active Data Guard when requested. Keep the label close to the Exadata-to-Exadata connector and avoid overlapping OCI automation/control-plane lines.
- Show OCI automation/control-plane relationships from OCI Parents Region / OCI Control Plane to the OCI child site, but avoid making control-plane lines louder than data-plane connectivity.
- Anchor each OCI Automation/control-plane connector at the left-side midpoint of the `OCI Control Plane` box and route it to the right-side midpoint of each AZ-specific `OCI Child Site` box. Do not terminate OCI Automation lines on the AWS Data Center, OCI VCN, Exadata icon, or parent AWS/AZ container boundary.

## OCI Parents Region Rendering

- Render OCI Parents Region using the standard OCI Region container style, not AWS region styling.
- Use the same visual hierarchy and label treatment as OCI Region rendering in the regular OCI diagram path.
- OCI Parents Region must be visually separate from the AWS Cloud/AWS Region boundary.
- OCI Parents Region must use OCI Region/grouping colors, not white or transparent fill. Use a visible gray OCI grouping fill with `#9E9892` line color.
- Center-align the `OCI Parents Region` label at the top of the OCI Parents Region container.
- Do not place an OCI icon badge inside the OCI Parents Region container header.
- Do not place explanatory text such as `Single OCI Parents Region` or `single-AD based view` inside the diagram body; keep this detail in notes when needed.
- Place OCI control plane inside OCI Parents Region when it is shown.
- Do not draw one OCI Parents Region container per AWS AZ. Multiple AWS AZ child-site deployments still share one OCI Parents Region container in this pattern.

## Diagram Titles

- Follow the common rendering guideline: use an architecture-specific title on the diagram slide, not an explanatory constraint sentence.
- For DR examples, prefer an English architecture title such as `ODB@AWS Multi-AZ DR Architecture`, even when slides 3 and 4 use Korean narrative content.

## Default Diagram Shape

```text
AWS Cloud
  AWS Region
    Availability Zone a
      Amazon VPC / application tier
      ODB network
      AWS data center
        OCI child site
          OCI VCN
            Client subnet
            Backup subnet
            Exadata databases
    Availability Zone b
      ODB network
      AWS data center
        OCI child site
          OCI VCN
            Client subnet
            Backup subnet
            Exadata databases

OCI Parents Region
  OCI control plane
```

## Notes And Best Practices

- State that CIDR overlap between the VPC, ODB network, and OCI VCN must be avoided.
- State that the VPC route table must route ODB network CIDRs through the ODB peering connection.
- State that Security Groups, NACLs, and DB listener access should allow only required application-to-database traffic.
- If Amazon S3 backup, direct S3 access, Amazon Redshift zero-ETL, or VPC Lattice integration is requested, render those as optional AWS service integration paths instead of adding them by default.
- If multiple VPCs access one ODB network, show Transit Gateway or Cloud WAN only when requested.
- For DR requests, add Data Guard/MAA, RTO/RPO, failover/failback, and runbook checkpoints explicitly.
