# AWS architecture visual standard

Read this for every AWS architecture, deployment, network, infrastructure, or
data-flow diagram. It defines the default visual language; the user's explicit
diagram instructions still take precedence.

The goal is an editable AWS diagram that reads immediately: inputs begin at the
top, each processing or storage stage follows below, network placement is
unambiguous, and the final deliverable is visibly the bottom-most outcome.

## Mandatory AWS icon rule

- Use an official draw.io AWS icon for every AWS service and AWS network
  construct shown. Prefer the current `mxgraph.aws4` resource or group icon.
- Run `python3 scripts/shapesearch.py "aws <service name>" --limit 5` for every
  distinct AWS service and select the result whose title and AWS4 style match
  the intended service. Never guess `resIcon`, `grIcon`, or stencil names.
- Preserve the official icon's aspect ratio and AWS service color. Use a
  consistent visual size, normally about 64–78 px for service icons.
- Put a short service label directly below the icon. Add a second line for its
  role only when the role is not obvious, for example `Lambda` followed by
  `Read API`.
- Do not replace Lambda, S3, RDS, API Gateway, EventBridge, Fargate, EC2, ELB,
  NAT Gateway, Internet Gateway, or another known AWS service with a generic
  rounded rectangle, cylinder, or text-only card.
- Use vendor icons for non-AWS products when available. Otherwise use a neutral
  external-system box. Never apply an AWS icon to Shopify, Google Ads,
  SharePoint, a user, an office network, or another non-AWS system.
- Generic boxes remain appropriate for business steps, scripts, transformations,
  or deliverables that are not themselves AWS services.

## Network boundary hierarchy

Use actual parent-child containment, not overlapping background rectangles.
When the architecture includes these scopes, nest them in this order:

```text
AWS Cloud
└── Region
    └── VPC
        ├── Availability Zone A
        │   ├── Public subnet
        │   └── Private subnet
        └── Availability Zone B
            ├── Public subnet
            └── Private subnet
```

- Label the AWS Cloud, Region, VPC, Availability Zone, and every depicted subnet.
- Every subnet label must say `Public subnet` or `Private subnet`. Add its name,
  tier, and CIDR when known, such as `Private application subnet · 10.0.20.0/24`.
- Never invent a region, Availability Zone, CIDR, subnet type, or resource
  placement. If the subnet type is known but the CIDR is not, label the subnet
  without a CIDR. If placement is unknown, keep the resource in an explicitly
  labeled `Placement TBD` area rather than guessing.
- Public and private subnets must be visually distinct. Default to a pale green
  tint for public subnets and a pale blue/teal tint for private subnets, while
  keeping enough contrast for dark or user-provided themes.
- Arrange Availability Zones side by side so repeated high-availability
  resources align horizontally. Arrange tiers vertically inside them.
- Put Internet Gateway, NAT Gateway, load balancers, bastions, compute, and
  databases inside the correct boundary supported by the source architecture.
- Show external inputs outside the VPC. Do not put SaaS sources or end users
  inside an AWS subnet.
- Do not add empty Cloud, Region, AZ, or subnet boxes merely for decoration.
  Boundaries must communicate deployment or security placement.

For exact AWS group styles, use `shapesearch.py` with queries such as `aws
cloud`, `aws region`, `aws availability zone`, `aws vpc`, `aws public subnet`,
and `aws private subnet`.

## Primary flow: top to bottom

The main story must read vertically from the top edge of the page to the bottom.
Use horizontal placement only to show parallel inputs, fan-out, replicas, or
Availability Zones at the same stage.

Use this row order when those stages exist; omit stages that are not part of the
real architecture:

1. **Inputs and actors** — users, SaaS systems, marketplaces, office systems,
   files, or upstream events. Place them in a horizontal source row at the top.
2. **Ingress or ingestion** — Internet Gateway, load balancer, EventBridge,
   ingestion Lambda, Fivetran, upload process, or equivalent entry point.
3. **Landing and processing** — S3 landing zone, queues, compute, Fargate tasks,
   application services, or transformation steps.
4. **Persistent data** — RDS, DynamoDB, S3 curated zones, logs, or other stores,
   placed inside their actual subnet or boundary.
5. **Serving layer** — read Lambda, API Gateway, authorization, application
   service, or another delivery interface.
6. **Final deliverable** — dashboard, application, report, MCP consumer, client
   experience, or other user-facing result. Place it at the bottom and label it
   as the outcome rather than leaving the flow ending at an infrastructure icon.

For a traditional three-tier web architecture, use the equivalent sequence:
user/internet → ingress/load balancing → web tier → application tier → database
tier. Replicas across Availability Zones stay on the same horizontal row.

If several inputs converge, keep them aligned across the top and route them into
one central ingestion lane. Keep the dominant processing path centered so a
viewer can trace it without scanning back upward.

## Arrows and reading direction

- Use directed orthogonal connectors with arrowheads for data, request, and
  deployment flows.
- Pin primary edges from bottom center to top center of the next stage so the
  main path is visibly downward.
- Label non-obvious edges with the payload, protocol, or action: `orders`,
  `CSV upload`, `HTTPS`, `events`, `SQL`, or `deploys`.
- Solid arrows represent the primary runtime or data path. Use dashed arrows
  for control-plane, deployment, optional, pending, or administrative paths and
  label what the dashed treatment means.
- Avoid upward primary arrows. If a response, feedback, or control path must go
  upward, route it through an outer corridor, style it differently, and label it.
- Keep connections between adjacent rows when possible. Long cross-tier edges
  use side corridors and must not pass through subnet labels or AWS icons.
- Run `scripts/edgeports.py` when nodes have multiple connections, then add
  explicit waypoints for any remaining crossings.

## Composition and visual treatment

- Put the diagram title at the top-left, outside the architecture boundaries.
- Use generous white space, aligned rows, equal icon sizing, and consistent
  label positions. Snap geometry to the grid.
- Prefer the clean icon-and-label treatment from AWS reference diagrams over
  large text-heavy cards. A card may group a logical process, but should not
  conceal the AWS services that perform it.
- Use restrained boundary fills and official AWS icon colors. A light or dark
  theme is acceptable; in either case preserve label contrast and boundary
  visibility.
- Use clear tier or stage labels when the diagram is large: `Inputs`, `Ingress`,
  `Processing`, `Data`, `Serving`, and `Final deliverable`.
- Make the final deliverable slightly more prominent with spacing, a subtle
  container, or stronger label weight. Do not make it visually louder than the
  entire architecture.
- Do not add a legend unless colors or line styles encode meanings that labels
  do not already explain.

## Visual QA checklist

Before presenting the draft, verify all of the following:

- Every AWS service has the correct official AWS icon and a readable label.
- No non-AWS product is represented by an AWS icon.
- All depicted subnets are visibly bounded and labeled public or private.
- Region, VPC, AZ, subnet, and resource nesting matches known architecture facts.
- Inputs occupy the top row and the final deliverable occupies the bottom row.
- The main flow can be followed downward without doubling back.
- Parallel AZ resources align on the same row and do not imply a false sequence.
- Arrow direction, labels, and dashed/solid semantics are clear.
- No edge crosses an icon, label, subnet title, or unrelated container.
- The diagram remains readable in the exported PNG at normal viewing size.
