# oci-archgen-skills

Skills for generating editable Oracle Cloud Infrastructure (OCI) architecture PowerPoint decks with Codex.

GitHub Pages preview: https://cdh3063.github.io/oci-archgen-skills/

## Included Skills

### `oci-arch-pptx`

Creates editable `.pptx` OCI architecture diagrams from natural-language architecture requests or structured JSON models.

Key capabilities:

- Region > VCN > subnet > service layout.
- OCI-style containers, subnet badges, gateway placement, and OSN handling.
- WAF, public/private LoadBalancer, redundant Web/App tiers, DataGuard, and service-gateway patterns.
- Editable PowerPoint output generated with deterministic OOXML.
- Model-aware validation for layout, required text coverage, and package structure.

## Install

Prerequisites:

- Git
- Bash
- Python 3.9 or later

Install all skills globally for Codex:

```bash
git clone https://github.com/cdh3063/oci-archgen-skills.git
cd oci-archgen-skills
./install.sh --all --tool codex
```

Install only `oci-arch-pptx`:

```bash
./install.sh oci-arch-pptx --tool codex
```

Other install targets:

```bash
./install.sh oci-arch-pptx --tool codex-local   # .codex/skills/<skill>
./install.sh oci-arch-pptx --tool codex-repo    # .agents/skills/<skill>
./install.sh oci-arch-pptx --tool claude        # ~/.claude/skills/<skill>
```

## Usage

After installation, ask Codex to use the skill:

```text
Use $oci-arch-pptx to create an editable OCI HA architecture PPTX with WAF,
redundant Web/App servers, public LoadBalancer, private App LoadBalancer,
and DataGuard.
```

You can also render from a structured model:

```bash
python3 ~/.codex/skills/oci-arch-pptx/scripts/generate_pptx.py \
  examples/ha-waf-dataguard-model.json \
  /tmp/ha-waf-dataguard.pptx

python3 ~/.codex/skills/oci-arch-pptx/scripts/validate_pptx.py \
  /tmp/ha-waf-dataguard.pptx \
  --model examples/ha-waf-dataguard-model.json
```

## Examples

- `examples/ha-waf-dataguard-model.json`
- `examples/ha-waf-dataguard.pptx`

## OCI Icons

This repository includes OCI icon assets used by the `oci-arch-pptx` skill, including `assets/OCI_Icons.pptx` and extracted icon assets.

Oracle Cloud Infrastructure icons, marks, and related brand assets remain the property of Oracle and are subject to Oracle's applicable brand and usage guidelines. This project is not affiliated with or endorsed by Oracle.

## Development

Install development dependencies:

```bash
python3 -m pip install -r requirements-dev.txt
```

Normal PPTX generation and model validation use only the Python standard library. The development dependency is used for Codex skill metadata validation.

Validate the skill metadata when the Codex `skill-creator` validator is available:

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  skills/oci-arch-pptx
```

Run the renderer and validator against the included example:

```bash
python3 skills/oci-arch-pptx/scripts/generate_pptx.py \
  examples/ha-waf-dataguard-model.json \
  /tmp/ha-waf-dataguard.pptx

python3 skills/oci-arch-pptx/scripts/validate_pptx.py \
  /tmp/ha-waf-dataguard.pptx \
  --model examples/ha-waf-dataguard-model.json
```

Run fixture validation:

```bash
for model in skills/oci-arch-pptx/fixtures/validation/*-model.json; do
  base="$(basename "$model" .json)"
  out="/tmp/${base}.pptx"
  python3 skills/oci-arch-pptx/scripts/generate_pptx.py "$model" "$out"
  python3 skills/oci-arch-pptx/scripts/validate_pptx.py "$out" --model "$model"
done
```

## License

Code in this repository is released under the MIT License. OCI icons and Oracle brand assets are not covered by the MIT License; see `NOTICE.md`.
