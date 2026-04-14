# DrawBot Redux

Design system for DrawBot with typography enforcement and CLI tooling.

## Install

Choose a backend:

### Native DrawBot (macOS, existing workflow)

```bash
uv sync --extra cli --extra drawbot
```

### drawbot-skia (cross-platform)

```bash
uv sync --extra cli --extra drawbot-skia
```

The CLI resolves backends in this order:
1. `--backend`
2. `DRAWBOT_BACKEND`
3. auto-detect (`drawBot` first, then `drawbot-skia`)

Phase 1 keeps existing DrawBot-first script workflows working as-is. `drawbot render`, `drawbot preview`, and `drawbot watch` still support scripts that directly use `import drawBot as db` when native DrawBot is installed. The new backend wrapper mainly powers repo-owned library/spec flows and newly scaffolded scripts.

## CLI

```bash
drawbot render script.py          # Render script
drawbot render script.py --open   # Render and open
drawbot render script.py --backend drawbot-skia
DRAWBOT_BACKEND=drawbot-skia drawbot from-spec poster.yaml
drawbot preview script.py         # Quick render + open
drawbot watch script.py           # Hot reload
drawbot new poster --template grid  # Scaffold from template
drawbot from-spec poster.yaml     # Render from YAML
drawbot templates list            # List templates

# Evolutionary form generation
drawbot evolve init               # Initialize project
drawbot evolve gen0 -n 16         # Generate initial population
drawbot evolve select gen_000 -w 1,2,3  # Select winners
drawbot evolve breed gen_000      # Breed next generation
drawbot evolve status             # Show evolution status
```

## Usage

```python
from drawbot_backend import db
from drawbot_grid import Grid
from drawbot_design_system import (
    POSTER_SCALE,
    setup_poster_page,
    draw_wrapped_text,
    get_output_path,
)

WIDTH, HEIGHT, MARGIN = setup_poster_page("letter")
grid = Grid.from_margins((-MARGIN,) * 4, column_subdivisions=12, row_subdivisions=8)
scale = POSTER_SCALE

db.fill(0.1)
db.rect(*grid[(0, 6)], *(grid * (12, 2)))

draw_wrapped_text("Hello DrawBot", MARGIN, HEIGHT - MARGIN, WIDTH - 2 * MARGIN, 120, "Helvetica", scale.body)
db.saveImage(str(get_output_path("poster.pdf")))
```

## Structure

```
├── cli/
│   ├── main.py        # CLI entry point
│   ├── spec.py        # YAML spec renderer
│   └── evolve/        # Evolutionary form generation
├── lib/               # Design system
├── examples/          # Example scripts
├── docs/              # guide.md, api.md
└── output/            # Rendered output
```

## Backend Notes

- New scaffolds now import `db` from `drawbot_backend`, so they can run on either supported backend.
- Existing user-authored scripts that directly import `drawBot` are still supported in the native DrawBot path.
- Phase 1 does not rewrite every example or arbitrary user script to become backend-neutral automatically.

## Docs

- [docs/guide.md](docs/guide.md) - Design system usage
- [docs/api.md](docs/api.md) - DrawBot API reference
