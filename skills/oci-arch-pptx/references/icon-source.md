# Icon Source

## Local Asset

Use `assets/OCI_Icons.pptx` as the bundled local icon source. It was copied from:

`/Users/ddchoi/Downloads/OCI_Icons.pptx`

The stable asset name inside the skill is `OCI_Icons.pptx` to avoid external path dependencies.

Use the local draw.io library as a secondary vector source for icons that are shape-only or unreliable in the PowerPoint extraction path:

`/Users/ddchoi/Downloads/OCI Style Guide for Drawio/OCI Library.xml`

The draw.io library stores icons as compressed mxGraph stencil paths, not embedded `data:image` files. Run `scripts/extract_drawio_icons.py` to convert matched stencil entries into SVG assets under `assets/extracted-icons/`. For generated PPTX compatibility, prefer `source_type: "drawio-raster"` PNG fallbacks rendered from those SVGs.

## Official Reference

Oracle documents the OCI Architecture Diagram Toolkit in PowerPoint, draw.io, and Visio formats:

https://docs.oracle.com/en-us/iaas/Content/General/Reference/graphicsfordiagrams.htm

Oracle states that these assets contain OCI service icons and templates where available, and that PowerPoint includes examples and guidance for creating deployment diagrams. This skill uses the PowerPoint asset as the source of truth.

## Mapping Policy

- Prefer exact OCI service icons from the toolkit.
- If exact icons cannot be extracted or matched, use the nearest OCI service-family icon and record the substitution.
- Do not use non-OCI vendor icons for OCI services.
- Keep labels explicit even when the icon is recognizable.

## Common Icon Keys

| Model type | Preferred icon key |
| --- | --- |
| `load-balancer` | `load-balancer` |
| `bastion` | `bastion` |
| `compute`, `web-server`, `app-server` | `compute` or `virtual-machine` |
| `database` | `database` |
| `exadata` | `exadata-database-service` or `exadata` |
| `vcn` | `virtual-cloud-network` |
| `subnet` | `subnet` |
| `internet-gateway` | `internet-gateway` |
| `nat-gateway` | `nat-gateway` |
| `service-gateway` | `service-gateway` |
| `drg` | `dynamic-routing-gateway` |
| `object-storage` | `object-storage` |
| `firewall` | `network-firewall` |

## Generated Mapping Files

- `references/icon-aliases.json`: required keys, aliases, and model fallback keys.
- `references/icon-map.json`: generated `icon_key` mapping. Entries with `asset_path` are ready for PPTX generation. Entries with `source_type: "shape-label"` need manual shape-copy support or a fallback.
- `references/icon-inventory.json`: generated review inventory of slides, text labels, pictures, and candidate matches.
- `references/drawio-icon-inventory.json`: generated review inventory for draw.io title matches and SVG stencil extraction.
- `assets/extracted-icons/`: generated image files referenced by `icon-map.json`.

Run extraction with:

```bash
scripts/extract_oci_icons.py
```

As of the current extraction, `references/icon-map.json` registers the drawable non-Logical/non-Physical OCI draw.io service icons as `drawio-raster` PNG assets. The only remaining non-draw.io-raster icon entry is `subnet`, which is a Physical grouping helper rather than a service icon.

Run selected draw.io extraction with:

```bash
scripts/extract_drawio_icons.py
```

Run full draw.io service PNG regeneration with:

```bash
scripts/extract_drawio_icons.py --all-services --asset-format png --replace-existing
qlmanage -t -s 512 -o skills/oci-arch-pptx/assets/extracted-icons skills/oci-arch-pptx/assets/extracted-icons/*.svg
scripts/finalize_drawio_png_icons.py
```

QuickLook previews of PPTX files do not reliably render embedded SVG icons, so the current `icon-map.json` points service entries to `*.drawio.png` PNG fallbacks while keeping the source SVG path in `source_drawio_svg`. `scripts/finalize_drawio_png_icons.py` removes border-connected white canvas backgrounds from the rendered PNGs.

## Extraction Notes

When implementing deterministic icon extraction, inspect the PPTX package under `ppt/media/` and slide relationships under `ppt/slides/_rels/`. Build a mapping table from nearby text labels to image filenames, then either reuse/copy those images into generated PPTX slides or keep duplicated editable shapes from the toolkit when a presentation runtime can import the source deck.
