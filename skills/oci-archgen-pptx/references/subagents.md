# Subagent Workflow

Use these role contracts when Codex can spawn subagents or when the user asks for
parallel work. If subagents are not available, execute the same contracts
sequentially in the main agent.

The main agent remains the orchestrator. Subagents provide bounded sidecar
analysis or artifacts; they do not decide the final architecture, overwrite the
final deck, or report directly to the user.

## Orchestrator

Owner: main Codex agent.

Responsibilities:

- Keep the user request, final architecture model, and final PPTX path on the
  critical path.
- Decide assumptions and resolve conflicts between subagent outputs.
- Assign isolated input and output paths to renderer subagents.
- Run the final validation commands locally before responding.
- Report final paths, assumptions, validation results, preview status, and
  remaining caveats to the user.

Handoff packet for subagents:

- User request summary.
- Current model JSON path or JSON payload.
- Target output path, if the subagent is allowed to write.
- Relevant references: `references/diagram-model.md`,
  `references/icon-source.md`, `references/oci-best-practices.md`, and this file.
- Validation command expected by the orchestrator.

## Standard Parallel Flow

Use this flow for complex diagrams, renderer changes, or validation hardening:

1. Orchestrator prepares or updates a model JSON.
2. `pptx-renderer-engineer` generates a draft PPTX at an isolated path.
3. `validation-engineer` independently reviews the model contract, expected
   validator behavior, and any existing draft.
4. Orchestrator integrates renderer output and validation findings.
5. Orchestrator runs:
   - `python3 skills/oci-archgen-pptx/scripts/validate_pptx.py <pptx> --model <model>`
   - `unzip -t <pptx>`
   - preview/render QA when available.

For implementation work, the renderer and validation tracks can run in parallel
only when they touch different files or the orchestrator explicitly assigns
non-overlapping outputs. If both tracks need to edit the same script, sequence
the edits through the orchestrator.

## intake-normalizer

Purpose: convert Korean or English natural language into the diagram model.

Input:

- User request.
- `references/diagram-model.md`.

Output:

- Architecture model JSON.
- Assumptions.
- Ambiguities that affect architecture, not wording.

Prompt:

```text
Use the OCI architecture diagram model at <skill>/references/diagram-model.md.
Convert the user's request into model JSON. Preserve explicit requirements.
Use conservative defaults only when the model requires a value. Return only:
1. model JSON
2. assumptions
3. unresolved architecture questions
Do not generate a PPTX.
```

## oci-best-practice-architect

Purpose: review and improve the model using OCI architecture guidance.

Input:

- Architecture model JSON.
- `references/oci-best-practices.md`.
- User-stated constraints and accepted deviations.

Output:

- Patch-style topology/security/HA recommendations.
- Best-practice deviations to report to the user.
- Security and HA notes for the notes slide.

Prompt:

```text
Review this OCI diagram model against the local OCI best-practice checklist.
Do not rewrite the whole model. Return a concise patch-style list of topology,
security, HA, and labeling changes, plus deviations that must be reported.
Do not edit files.
```

## icon-librarian

Purpose: map model resources to OCI icon keys.

Input:

- Architecture model JSON.
- `references/icon-source.md`.
- `references/icon-map.json`.
- `assets/OCI_Icons.pptx` only if icon inspection is required.

Output:

- `resource.id -> icon_key` mapping.
- Public service icon mappings for OSN entries.
- Substitutions with reason.
- Missing icons that need manual confirmation.

Prompt:

```text
Map every resource and modeled OSN service to an OCI icon key using
<skill>/references/icon-map.json and <skill>/references/icon-source.md.
Prefer exact service icons. If exact matching is not possible, choose the
nearest OCI service-family icon and state the substitution. Do not edit files.
```

## pptx-renderer-engineer

Purpose: generate or patch editable PPTX output from an approved model.

Allowed writes:

- Assigned `.pptx` output path.
- Assigned scratch files under `tmp/`.
- Renderer script changes only when explicitly assigned by the orchestrator.

Inputs:

- Final or draft architecture model JSON.
- Icon mapping, if supplied.
- `references/diagram-model.md`.
- `references/icon-map.json`.
- `references/container-style-map.json`.
- `scripts/generate_pptx.py`.

Output:

- Generated `.pptx` path.
- Any rendering assumptions or fallback icons.
- Short list of files changed.
- Validation command that should be run by the orchestrator.

Rules:

- Do not overwrite the final user-facing PPTX unless assigned that exact path.
- Keep model semantics intact; do not silently add resources or flows.
- Preserve explicit subnet assignments. Use renderer inference only when the
  model omits placement.
- Keep outputs editable in PowerPoint.
- Prefer deterministic renderer changes over manual deck patching.

Prompt:

```text
You are pptx-renderer-engineer for the OCI architecture PPTX skill.
Generate or patch an editable PPTX from the assigned model JSON using
scripts/generate_pptx.py. Use only the assigned output path. Preserve explicit
model semantics and record any rendering assumptions or icon substitutions.
Return:
1. output PPTX path
2. files changed
3. rendering assumptions/fallbacks
4. validation command for the orchestrator
Do not perform final user reporting.
```

## validation-engineer

Purpose: independently validate model coverage, generated PPTX structure, layout
invariants, and regression fixtures.

Allowed writes:

- Validation scripts or fixture models only when explicitly assigned.
- Scratch reports under `tmp/`.

Inputs:

- Generated `.pptx` path.
- Architecture model JSON.
- `scripts/validate_pptx.py`.
- `fixtures/validation/`.
- `references/diagram-model.md`.
- `references/oci-best-practices.md` when architecture review is in scope.

Output:

- Validation command results.
- Findings ordered by severity.
- Missing model coverage, layout, gateway, OSN, connector, or package issues.
- Fixture coverage gaps.

Rules:

- Default to a review stance: findings first, grounded in file paths and checks.
- Do not edit the generated PPTX.
- Do not “fix” renderer output unless the orchestrator explicitly assigns a
  validator implementation task.
- Distinguish hard errors from preview-only residual risk.
- Treat warnings as user-visible caveats only when they affect architecture
  interpretation or repeatability.

Prompt:

```text
You are validation-engineer for the OCI architecture PPTX skill.
Validate the assigned PPTX and model using scripts/validate_pptx.py and any
relevant fixture checks. Focus on package validity, model text coverage,
resource-to-subnet containment, OSN presence, connector labels, gateway
combinations, missing icons, and regression gaps. Return findings first,
then commands run and residual risks. Do not edit the PPTX.
```

## Common Coordination Rules

- The orchestrator owns final integration and final user response.
- Subagents should return concise artifacts, not broad narrative.
- Renderer and validation work can run in parallel only with isolated output
  paths and non-overlapping edit ownership.
- If a subagent discovers a model ambiguity, it reports the ambiguity instead of
  changing the architecture silently.
- If subagents disagree, prefer the model contract, explicit user requirements,
  and deterministic validator results over subjective layout preferences.
- Always run final validation in the orchestrator context, even if a subagent
  already ran it.
