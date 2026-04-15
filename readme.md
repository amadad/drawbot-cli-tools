# drawbot

A radically minimal, headless DrawBot CLI built on bundled upstream `drawbot-skia` source.

## High-level branded artifact workflow

The repo's primary agent-native path is now the branded `social-quote` flow:

```bash
drawbot design validate DESIGN.md
drawbot design explain DESIGN.md
drawbot recipe validate fixtures/brand_artifacts/social-quote.recipe.yaml
drawbot recipe explain fixtures/brand_artifacts/social-quote.recipe.yaml
drawbot create social-quote --design DESIGN.md --recipe fixtures/brand_artifacts/social-quote.recipe.yaml --data fixtures/brand_artifacts/social-quote.content.yaml -o out/social-quote
```

That flow moves through these artifacts in order:

1. `DESIGN.md` defines the brand contract and tokens.
2. `fixtures/brand_artifacts/social-quote.recipe.yaml` locks the artifact family, geometry, and canonical embedded copy.
3. `fixtures/brand_artifacts/social-quote.content.yaml` provides the authoring content payload.
4. `drawbot create social-quote ...` expands those inputs into deterministic internal specs.
5. Each generated spec is linted, lint-clean variants are rendered to PDF, and `manifest.json` records the result.

For a worked example, see `fixtures/brand_artifacts/WORKFLOW.md`.

## Command surface

### High-level artifact commands

```bash
drawbot create social-quote --design DESIGN.md --recipe fixtures/brand_artifacts/social-quote.recipe.yaml --data fixtures/brand_artifacts/social-quote.content.yaml -o out/social-quote
drawbot design validate DESIGN.md
drawbot design explain DESIGN.md
drawbot recipe validate fixtures/brand_artifacts/social-quote.recipe.yaml
drawbot recipe explain fixtures/brand_artifacts/social-quote.recipe.yaml
```

### Runtime and low-level commands

```bash
drawbot doctor
drawbot run script.py -o output.png
drawbot new name
drawbot api list
drawbot api show SYMBOL
drawbot api gaps
drawbot spec validate poster.yaml
drawbot spec explain poster.yaml
drawbot spec render poster.yaml -o poster.pdf
```

## Layout

```text
vendor/                # bundled upstream drawbot-skia source
drawbot_cli/           # active CLI code
tests/                 # active v2 tests only
_archive/              # brownfield code kept for reference
```

## Install

This repo bundles the upstream source locally, but you still need the runtime dependencies.

```bash
uv sync
```

Then verify the setup:

```bash
drawbot doctor
```

`doctor` reports the bundled source paths, imported module, runtime version, and status.

## Run a script

```bash
drawbot run poster.py -o output/poster.png
```

The `run` command delegates directly to the bundled upstream `drawbot-skia` runner.

## Inspect the runtime surface

```bash
drawbot api list
drawbot api show newPage
drawbot api gaps
```

The `api` group introspects the exported `drawbot_skia.drawbot` surface without adding another abstraction layer.

## Create a branded artifact from fixtures

```bash
uv run drawbot create social-quote \
  --design DESIGN.md \
  --recipe fixtures/brand_artifacts/social-quote.recipe.yaml \
  --data fixtures/brand_artifacts/social-quote.content.yaml \
  -n 4 \
  -o out/social-quote \
  --seed 7
```

Expected outputs:

- `social-quote-01.yaml` ... `social-quote-04.yaml`
- `social-quote-01.pdf` ... `social-quote-04.pdf` for lint-clean variants
- `manifest.json` with summary totals, per-variant lint payloads, warnings, and render status

Use `drawbot design explain` and `drawbot recipe explain` when you need to inspect the resolved contract before generation.

## Render a simple YAML spec

The current spec layer is intentionally small: absolute positioning, page presets (`letter`, `a4`, `tabloid`, `square`), and five element types: `rect`, `oval`, `line`, `text`, and `image`.

```yaml
page:
  format: letter
  background: "#ffffff"

elements:
  - type: rect
    x: 72
    y: 72
    width: 200
    height: 120
    fill: "#111111"

  - type: text
    text: "Hello DrawBot"
    x: 72
    y: 240
    font: Helvetica
    font_size: 36
```

```bash
drawbot spec validate poster.yaml
drawbot spec explain poster.yaml
drawbot spec render poster.yaml -o output/poster.pdf
```

If `--output` is omitted, `spec render` writes beside the YAML file as `<name>.pdf`.

## Scope

This repo is now intentionally narrow:
- skia-native only
- headless only
- no backend switching
- no native DrawBot compatibility layer
- simple commands first, one real capability at a time

Anything from the previous brownfield implementation lives under `_archive/` and is reference-only.
