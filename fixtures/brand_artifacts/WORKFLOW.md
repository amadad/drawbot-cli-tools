# Social quote workflow example

This fixture set is the repo's worked example for the agent-native branded artifact path.

## Inputs

- `../../DESIGN.md` defines the brand contract, tokens, allowed inputs, and the canonical command surface.
- `social-quote.recipe.yaml` defines the locked `social-quote` geometry and the embedded canonical copy for the v1 command path.
- `social-quote.content.yaml` is the authoring content fixture with the required `quote`, `author`, and `source` fields.
- `social-quote.review.yaml` defines the human or automated review checks for the rendered artifact.

## End-to-end commands

Validate the design and recipe first:

```bash
uv run drawbot design validate DESIGN.md
uv run drawbot recipe validate fixtures/brand_artifacts/social-quote.recipe.yaml
```

Explain the effective contract:

```bash
uv run drawbot design explain DESIGN.md
uv run drawbot recipe explain fixtures/brand_artifacts/social-quote.recipe.yaml
```

Generate deterministic variants, lint them, render passing outputs, and write a manifest:

```bash
uv run drawbot create social-quote \
  --design DESIGN.md \
  --recipe fixtures/brand_artifacts/social-quote.recipe.yaml \
  --data fixtures/brand_artifacts/social-quote.content.yaml \
  -n 4 \
  -o out/social-quote \
  --seed 7
```

## Expected outputs

The create command writes:

- `out/social-quote/social-quote-01.yaml` ... `social-quote-04.yaml` — deterministic internal specs
- `out/social-quote/social-quote-01.pdf` ... `social-quote-04.pdf` — rendered outputs for lint-clean variants
- `out/social-quote/manifest.json` — machine-readable summary of inputs, variants, lint results, warnings, and render status

## What the manifest proves

`manifest.json` is the handoff record for downstream review or publishing. It captures:

- the exact design, recipe, and data inputs
- the deterministic seed and variant count
- each variant's chosen layout
- the generated spec filename
- whether a PDF was rendered
- machine-readable lint status and issues

If lint fails for a variant, the spec still exists for inspection and the manifest records `rendered: false` with the failure details.
