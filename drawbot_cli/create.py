from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from drawbot_cli.design import DesignDocument, normalize_design
from drawbot_cli.recipes.core import load_recipe, validate_recipe
from drawbot_cli.spec.core import validate_spec


@dataclass(frozen=True)
class CreateResult:
    output_dir: Path
    manifest_path: Path
    spec_paths: list[Path]


def load_content(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("Top-level content must be a mapping.")
    return data


def create_social_quote_specs(
    design_document: DesignDocument,
    recipe_path: Path,
    data_path: Path,
    output_dir: Path,
    count: int = 4,
    seed: int = 1,
) -> CreateResult:
    if count < 1:
        raise ValueError("count must be at least 1")

    normalized_design = normalize_design(design_document)
    recipe_path = recipe_path.resolve()
    recipe = load_recipe(recipe_path)
    recipe_errors = validate_recipe(recipe, recipe_path=recipe_path)
    if recipe_errors:
        raise ValueError("; ".join(recipe_errors))

    content = load_content(data_path.resolve())
    missing = [field for field in ("quote", "author", "source") if not isinstance(content.get(field), str) or not content[field].strip()]
    if missing:
        raise ValueError("; ".join(f"content missing required field: {field}" for field in missing))

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    spec_paths: list[Path] = []
    manifest_variants: list[dict[str, Any]] = []
    for index in range(count):
        variant_seed = seed + index
        spec = _build_social_quote_spec(normalized_design, recipe, content, variant_seed, index)
        errors = validate_spec(spec)
        if errors:
            raise ValueError("; ".join(errors))
        spec_path = output_dir / f"social-quote-{index + 1:02d}.yaml"
        spec_path.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")
        spec_paths.append(spec_path)
        manifest_variants.append(
            {
                "id": f"social-quote-{index + 1:02d}",
                "seed": variant_seed,
                "layout": spec["metadata"]["layout"],
                "spec": spec_path.name,
            }
        )

    manifest = {
        "artifact": "social-quote",
        "generator": "drawbot create social-quote",
        "seed": seed,
        "count": count,
        "inputs": {
            "design": str(design_document.path),
            "recipe": str(recipe_path),
            "data": str(data_path.resolve()),
        },
        "variants": manifest_variants,
        "review": {
            "status": "stub",
            "notes": "Review generated specs against DESIGN.md and recipe constraints before render/publish.",
        },
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return CreateResult(output_dir=output_dir, manifest_path=manifest_path, spec_paths=spec_paths)


def _build_social_quote_spec(
    design: dict[str, Any], recipe: dict[str, Any], content: dict[str, Any], seed: int, index: int
) -> dict[str, Any]:
    rng = random.Random(seed)
    page = dict(recipe.get("page") or {})
    safe_zone = dict(recipe.get("safe_zone") or {})
    placements = dict(recipe.get("placements") or {})

    panel = dict(placements["panel"])
    accent = dict(placements["accent_bar"])
    quote_box = dict(placements["quote"])
    author_box = dict(placements["author"])
    source_box = dict(placements["source"])

    layout_name = _layout_name(index)
    padding = design["composition"]["spacing"]["outer_padding"]
    quote_gap = design["composition"]["spacing"]["quote_gap"]

    inset_choices = [0, 24, 48]
    accent_inset = inset_choices[rng.randrange(len(inset_choices))]
    accent_height = [16, 20, 24][rng.randrange(3)]
    panel_fill = design["palette"]["panel"]

    quote_size = max(56, design["type"]["quote_size"] - 4 * (index % 3))
    author_size = design["type"]["attribution_size"]
    source_size = max(24, author_size - 4)

    safe_x = float(safe_zone["x"])
    safe_y = float(safe_zone["y"])
    safe_w = float(safe_zone["width"])
    safe_h = float(safe_zone["height"])

    if layout_name == "top-heavy":
        quote_box["y"] = safe_y + safe_h - 340
        author_box["y"] = quote_box["y"] - 110
        source_box["y"] = author_box["y"] - 46
    elif layout_name == "middle-stack":
        quote_box["y"] = safe_y + (safe_h * 0.48)
        author_box["y"] = quote_box["y"] - 130
        source_box["y"] = author_box["y"] - 50
    elif layout_name == "lower-anchor":
        quote_box["y"] = safe_y + 470
        author_box["y"] = quote_box["y"] - 140
        source_box["y"] = author_box["y"] - 52
    else:
        quote_box["y"] = safe_y + 560
        author_box["y"] = quote_box["y"] - 128
        source_box["y"] = author_box["y"] - 48

    quote_box["x"] = safe_x + padding * 0.0
    quote_box["width"] = safe_w
    quote_box["height"] = max(280, float(quote_box["height"]))
    author_box["x"] = quote_box["x"]
    author_box["width"] = quote_box["width"]
    source_box["x"] = quote_box["x"]
    source_box["width"] = quote_box["width"]

    accent["x"] = panel["x"] + accent_inset
    accent["width"] = panel["width"] - accent_inset * 2
    accent["height"] = accent_height
    accent["y"] = panel["y"] + panel["height"] - padding + (index % 2) * (quote_gap / 3)

    return {
        "page": {
            "width": int(page["width"]),
            "height": int(page["height"]),
            "background": page.get("background", design["palette"]["background"]),
        },
        "metadata": {
            "artifact": "social-quote",
            "layout": layout_name,
            "seed": seed,
        },
        "output": {
            "format": recipe.get("variants", {}).get("format", "social-quote-portrait"),
        },
        "elements": [
            {
                "type": "rect",
                "x": panel["x"],
                "y": panel["y"],
                "width": panel["width"],
                "height": panel["height"],
                "fill": panel_fill,
            },
            {
                "type": "rect",
                "x": accent["x"],
                "y": accent["y"],
                "width": accent["width"],
                "height": accent["height"],
                "fill": design["palette"]["accent"],
            },
            {
                "type": "text",
                "text": content["quote"].strip(),
                "x": quote_box["x"],
                "y": round(float(quote_box["y"]), 2),
                "font": design["type"]["quote_font"],
                "font_size": quote_size,
                "fill": design["palette"]["text"],
            },
            {
                "type": "text",
                "text": f"— {content['author'].strip()}",
                "x": author_box["x"],
                "y": round(float(author_box["y"]), 2),
                "font": design["type"]["attribution_font"],
                "font_size": author_size,
                "fill": design["palette"]["muted"],
            },
            {
                "type": "text",
                "text": content["source"].strip(),
                "x": source_box["x"],
                "y": round(float(source_box["y"]), 2),
                "font": design["type"].get("source_font", design["type"]["attribution_font"]),
                "font_size": source_size,
                "fill": design["palette"]["muted"],
            },
        ],
    }


def _layout_name(index: int) -> str:
    return ["balanced", "top-heavy", "middle-stack", "lower-anchor"][index % 4]
