from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


REQUIRED_TOP_LEVEL_FIELDS = (
    "contract_version",
    "brand",
    "artifact",
    "inputs",
    "canvas",
    "tokens",
    "rules",
)
REQUIRED_COLOR_TOKENS = ("background", "panel", "accent", "text", "muted")
REQUIRED_TYPOGRAPHY_TOKENS = ("quote_font", "quote_size", "attribution_font", "attribution_size")
REQUIRED_SPACING_TOKENS = ("outer_padding", "quote_gap")


@dataclass(frozen=True)
class DesignDocument:
    path: Path
    sections: dict[str, str]
    data: dict[str, Any]


def load_design(path: Path) -> DesignDocument:
    text = path.read_text(encoding="utf-8")
    sections = _parse_markdown_sections(text)
    data = _extract_contract_block(text)
    if not isinstance(data, dict):
        raise ValueError("DESIGN.md contract block must be a YAML mapping.")
    return DesignDocument(path=path.resolve(), sections=sections, data=data)


def validate_design(document: DesignDocument) -> list[str]:
    data = document.data
    errors: list[str] = []

    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in data:
            errors.append(f"missing {field}")

    brand = _mapping(data.get("brand"), "brand", errors)
    artifact = _mapping(data.get("artifact"), "artifact", errors)
    inputs = _mapping(data.get("inputs"), "inputs", errors)
    canvas = _mapping(data.get("canvas"), "canvas", errors)
    tokens = _mapping(data.get("tokens"), "tokens", errors)

    if brand is not None:
        _require_keys(brand, "brand", ("id", "name"), errors)
    if artifact is not None:
        _require_keys(artifact, "artifact", ("family", "command_path"), errors)
    if inputs is not None:
        _require_keys(inputs, "inputs", ("recipe", "content_example", "review_rubric"), errors)
    if canvas is not None:
        _require_keys(canvas, "canvas", ("width", "height"), errors)
    if isinstance(canvas, dict):
        for key in ("width", "height"):
            if key in canvas and not isinstance(canvas[key], int):
                errors.append(f"canvas.{key} must be an integer")

    colors = typography = spacing = None
    if tokens is not None:
        colors = _mapping(tokens.get("colors"), "tokens.colors", errors)
        typography = _mapping(tokens.get("typography"), "tokens.typography", errors)
        spacing = _mapping(tokens.get("spacing"), "tokens.spacing", errors)

    if colors is not None:
        _require_keys(colors, "tokens.colors", REQUIRED_COLOR_TOKENS, errors)
    if typography is not None:
        _require_keys(typography, "tokens.typography", REQUIRED_TYPOGRAPHY_TOKENS, errors)
    if spacing is not None:
        _require_keys(spacing, "tokens.spacing", REQUIRED_SPACING_TOKENS, errors)

    rules = data.get("rules")
    if rules is not None and not isinstance(rules, list):
        errors.append("rules must be a list")

    return errors


def normalize_design(document: DesignDocument) -> dict[str, Any]:
    errors = validate_design(document)
    if errors:
        raise ValueError("; ".join(errors))

    data = document.data
    brand = data["brand"]
    artifact = data["artifact"]
    inputs = data["inputs"]
    canvas = data["canvas"]
    tokens = data["tokens"]

    return {
        "contract_version": int(data["contract_version"]),
        "brand": {
            "id": str(brand["id"]),
            "name": str(brand["name"]),
        },
        "artifact": {
            "family": str(artifact["family"]),
            "command_path": str(artifact["command_path"]),
        },
        "inputs": {
            "recipe": str(inputs["recipe"]),
            "content_example": str(inputs["content_example"]),
            "review_rubric": str(inputs["review_rubric"]),
        },
        "palette": {key: str(tokens["colors"][key]) for key in REQUIRED_COLOR_TOKENS},
        "type": {
            "quote_font": str(tokens["typography"]["quote_font"]),
            "quote_size": int(tokens["typography"]["quote_size"]),
            "attribution_font": str(tokens["typography"]["attribution_font"]),
            "attribution_size": int(tokens["typography"]["attribution_size"]),
        },
        "composition": {
            "canvas": {
                "width": int(canvas["width"]),
                "height": int(canvas["height"]),
            },
            "spacing": {
                "outer_padding": int(tokens["spacing"]["outer_padding"]),
                "quote_gap": int(tokens["spacing"]["quote_gap"]),
            },
        },
        "rules": [str(rule) for rule in data.get("rules", [])],
        "prose": {
            "scope": document.sections.get("Scope", ""),
            "guidance": document.sections.get("Guidance", ""),
        },
    }


def explain_design(document: DesignDocument) -> dict[str, Any]:
    normalized = normalize_design(document)
    return {
        "contract_version": normalized["contract_version"],
        "brand": normalized["brand"],
        "artifact": normalized["artifact"],
        "palette": normalized["palette"],
        "type": normalized["type"],
        "composition": normalized["composition"],
        "prose_summary": {key: _summarize(value) for key, value in normalized["prose"].items() if value},
    }


def _extract_contract_block(text: str) -> Any:
    lines = text.splitlines()
    inside = False
    block_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not inside:
            if stripped in {"```yaml", "```yml"}:
                inside = True
            continue
        if stripped == "```":
            return yaml.safe_load("\n".join(block_lines))
        block_lines.append(line)
    raise ValueError("DESIGN.md is missing a fenced YAML contract block.")


def _parse_markdown_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
            continue
        if current is not None:
            sections[current].append(line)
    return {name: "\n".join(lines).strip() for name, lines in sections.items()}


def _mapping(value: Any, name: str, errors: list[str]) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        errors.append(f"{name} must be a mapping")
        return None
    return value


def _require_keys(mapping: dict[str, Any], prefix: str, keys: tuple[str, ...], errors: list[str]) -> None:
    for key in keys:
        if key not in mapping:
            errors.append(f"missing {prefix}.{key}")


def _summarize(text: str) -> str:
    parts = [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("```")]
    return " ".join(parts)
