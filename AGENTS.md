# drawbot

Skia-native, headless DrawBot CLI.

## Active surface

- `vendor/` — bundled upstream `drawbot-skia` source
- `drawbot_cli/` — active CLI package
- `tests/` — active v2 tests
- `_archive/` — brownfield reference only

Key active modules:
- `drawbot_cli/runtime/skia.py` — runtime import boundary into bundled upstream code
- `drawbot_cli/commands/` — CLI command groups (`doctor`, `run`, `new`, `api`, `spec`)
- `drawbot_cli/spec/core.py` — minimal YAML spec validation and rendering

## Current commands

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

## Rules

- Build in `drawbot_cli/`, not `_archive/`
- No native DrawBot compatibility layer
- No backend switching
- Keep the CLI radically minimal
- Extend `drawbot_cli/spec/core.py` incrementally instead of reviving `_archive/cli/spec.py` wholesale
- Prefer simple integration tests over broad mock-heavy systems
- Use `trash`, not `rm`
