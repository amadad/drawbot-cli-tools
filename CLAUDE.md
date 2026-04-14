# drawbot

This repo is a radically minimal, skia-native, headless DrawBot CLI.

## What is active

- `vendor/` — bundled upstream `drawbot-skia` source we can inspect and modify
- `drawbot_cli/` — active CLI code
- `tests/` — active v2 tests only

Key active modules:
- `drawbot_cli/runtime/skia.py` — runtime import boundary into bundled upstream code
- `drawbot_cli/commands/` — CLI command groups (`doctor`, `run`, `new`, `api`, `spec`)
- `drawbot_cli/spec/core.py` — minimal YAML spec validation and rendering

## What is not active

- `_archive/` contains the old brownfield implementation
- Treat `_archive/` as reference only unless explicitly porting something small

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

## Guidance

- Prefer deleting complexity over preserving legacy abstractions
- Keep the command surface small and honest
- Add one real capability at a time
- Extend the current spec layer incrementally instead of reviving the old brownfield spec system wholesale
- Do not reintroduce backend selection or native DrawBot compatibility unless explicitly requested

## Current gotchas

- `drawbot doctor` now reports bundled source paths, module name, version, and status
- `drawbot api` introspects the exported `drawbot_skia.drawbot` surface directly
- `drawbot spec` is intentionally small right now: page presets plus `rect`, `oval`, `line`, `text`, and `image`
- `drawbot spec render` defaults to writing `<spec>.pdf` beside the YAML file when `--output` is omitted
