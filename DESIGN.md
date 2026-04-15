# Brand artifact contract v1

This repo's first brand-aware output path is intentionally narrow: one brand, one artifact family, one command path.

## Scope

- Brand: `acme`
- Artifact family: `social-quote`
- Command path: `drawbot spec render fixtures/brand_artifacts/social-quote.recipe.yaml -o out/social-quote.pdf`
- Input model: executable recipe + canonical content fixture

```yaml
contract_version: 1
brand:
  id: acme
  name: Acme
artifact:
  family: social-quote
  command_path: drawbot spec render fixtures/brand_artifacts/social-quote.recipe.yaml -o out/social-quote.pdf
inputs:
  recipe: fixtures/brand_artifacts/social-quote.recipe.yaml
  content_example: fixtures/brand_artifacts/social-quote.content.yaml
  review_rubric: fixtures/brand_artifacts/social-quote.review.yaml
canvas:
  width: 1080
  height: 1350
tokens:
  colors:
    background: "#0F172A"
    panel: "#111827"
    accent: "#F59E0B"
    text: "#F8FAFC"
    muted: "#CBD5E1"
  typography:
    quote_font: Helvetica-Bold
    quote_size: 72
    attribution_font: Helvetica
    attribution_size: 32
    source_font: Helvetica
    source_size: 28
  spacing:
    outer_padding: 96
    quote_gap: 36
rules:
  - recipe must target artifact.family == social-quote
  - content fixture must provide quote, author, and source fields matching the canonical example copy
  - executable recipe must embed that canonical copy directly for the locked v1 command path
  - recipe output page must match canvas width and height
  - implementations may add layout logic but may not invent new tokens
```

## Workflow architecture

The branded artifact pipeline is intentionally explicit:

1. `DESIGN.md` is the contract source of truth for brand identity, tokens, canvas, and allowed inputs.
2. `fixtures/brand_artifacts/social-quote.recipe.yaml` locks the executable artifact family, page geometry, placements, and the canonical embedded copy required by the v1 command path.
3. `fixtures/brand_artifacts/social-quote.content.yaml` is the authoring content payload for `quote`, `author`, and `source`.
4. `drawbot create social-quote` combines the design contract, recipe, and content into deterministic internal specs.
5. The create pipeline lints each spec against design tokens, recipe placements, and required content fields.
6. Lint-clean variants render to PDF, and `manifest.json` records every generated spec, render outcome, lint payload, and warning.
7. `fixtures/brand_artifacts/social-quote.review.yaml` is the final review checklist for a human or agent before publish.

## Guidance

The contract exists so downstream agent tasks can generate one real branded artifact without guessing.

Keep the v1 implementation specific:

- Do not add a multi-brand registry.
- Do not add generic theme inheritance.
- Do not add artifact discovery conventions beyond these explicit files.
- Treat the token block above as the validation source of truth.

The recipe should map these tokens onto the current `drawbot spec` surface as directly as possible. For v1, the documented command path is intentionally locked to one executable recipe, so the canonical quote copy is embedded directly in the recipe instead of being templated at render time. The content fixture remains the authoring reference for the same required fields. The review rubric gives a concrete success check for human or automated review.

## Worked example: social-quote

Validate and inspect the inputs:

```bash
uv run drawbot design validate DESIGN.md
uv run drawbot recipe validate fixtures/brand_artifacts/social-quote.recipe.yaml
uv run drawbot design explain DESIGN.md
uv run drawbot recipe explain fixtures/brand_artifacts/social-quote.recipe.yaml
```

Generate the artifact set:

```bash
uv run drawbot create social-quote \
  --design DESIGN.md \
  --recipe fixtures/brand_artifacts/social-quote.recipe.yaml \
  --data fixtures/brand_artifacts/social-quote.content.yaml \
  -n 4 \
  -o out/social-quote \
  --seed 7
```

The resulting `out/social-quote/manifest.json` should summarize:

- `artifact: social-quote`
- `summary.total: 4`
- `summary.rendered: 4` when all variants pass lint
- per-variant `layout`, `spec`, `output`, `rendered`, `warnings`, and machine-readable `lint`

The repo fixture walkthrough in `fixtures/brand_artifacts/WORKFLOW.md` documents the same path end to end.
