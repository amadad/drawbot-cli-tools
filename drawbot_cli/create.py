from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from drawbot_cli.design import DesignDocument, normalize_design
from drawbot_cli.recipes.core import SOCIAL_QUOTE_REQUIRED_FIELDS, load_recipe, validate_recipe
from drawbot_cli.spec.core import render_spec, validate_spec


HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True)
class LintIssue:
    code: str
    message: str
    level: str = "error"
    element_index: int | None = None


@dataclass(frozen=True)
class VariantArtifact:
    id: str
    seed: int
    layout: str
    spec_path: Path
    output_path: Path | None
    lint: dict[str, Any]
    warnings: list[str]
    rendered: bool


@dataclass(frozen=True)
class CreateResult:
    output_dir: Path
    manifest_path: Path
    spec_paths: list[Path]
    output_paths: list[Path]
    variants: list[VariantArtifact]


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
    render: bool = True,
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

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    spec_paths: list[Path] = []
    output_paths: list[Path] = []
    variant_artifacts: list[VariantArtifact] = []
    manifest_variants: list[dict[str, Any]] = []
    for index in range(count):
        variant_seed = seed + index
        variant_id = f"social-quote-{index + 1:02d}"
        spec = _build_social_quote_spec(normalized_design, recipe, content, variant_seed, index)
        lint_issues = lint_social_quote_variant(
            spec=spec,
            content=content,
            design=normalized_design,
            recipe=recipe,
        )
        lint_payload = _lint_payload(lint_issues)

        spec_path = output_dir / f"{variant_id}.yaml"
        spec_path.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")
        spec_paths.append(spec_path)

        output_path: Path | None = None
        if lint_payload["ok"] and render:
            output_path = output_dir / f"{variant_id}.pdf"
            render_spec(spec_path, output_path)
            output_paths.append(output_path)

        variant = VariantArtifact(
            id=variant_id,
            seed=variant_seed,
            layout=spec["metadata"]["layout"],
            spec_path=spec_path,
            output_path=output_path,
            lint=lint_payload,
            warnings=[issue.message for issue in lint_issues if issue.level == "warning"],
            rendered=output_path is not None,
        )
        variant_artifacts.append(variant)
        manifest_variants.append(
            {
                "id": variant.id,
                "seed": variant.seed,
                "layout": variant.layout,
                "spec": variant.spec_path.name,
                "output": variant.output_path.name if variant.output_path else None,
                "rendered": variant.rendered,
                "warnings": variant.warnings,
                "lint": variant.lint,
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
        "summary": {
            "total": len(variant_artifacts),
            "rendered": sum(1 for variant in variant_artifacts if variant.rendered),
            "failed_lint": sum(1 for variant in variant_artifacts if not variant.lint["ok"]),
        },
        "review": {
            "status": "stub",
            "notes": "Review generated specs against DESIGN.md and recipe constraints before render/publish.",
        },
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return CreateResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        spec_paths=spec_paths,
        output_paths=output_paths,
        variants=variant_artifacts,
    )


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
                "text": str(content.get("quote", "")).strip(),
                "x": quote_box["x"],
                "y": round(float(quote_box["y"]), 2),
                "font": design["type"]["quote_font"],
                "font_size": quote_size,
                "fill": design["palette"]["text"],
            },
            {
                "type": "text",
                "text": f"— {str(content.get('author', '')).strip()}",
                "x": author_box["x"],
                "y": round(float(author_box["y"]), 2),
                "font": design["type"]["attribution_font"],
                "font_size": author_size,
                "fill": design["palette"]["muted"],
            },
            {
                "type": "text",
                "text": str(content.get("source", "")).strip(),
                "x": source_box["x"],
                "y": round(float(source_box["y"]), 2),
                "font": design["type"].get("source_font", design["type"]["attribution_font"]),
                "font_size": source_size,
                "fill": design["palette"]["muted"],
            },
        ],
    }


def lint_social_quote_variant(
    spec: dict[str, Any],
    content: dict[str, Any],
    design: dict[str, Any],
    recipe: dict[str, Any],
) -> list[LintIssue]:
    issues: list[LintIssue] = []

    for field in SOCIAL_QUOTE_REQUIRED_FIELDS:
        value = content.get(field)
        if not isinstance(value, str) or not value.strip():
            issues.append(LintIssue(code=f"content.missing_{field}", message=f"content missing required field: {field}"))

    for error in validate_spec(spec):
        issues.append(LintIssue(code="spec.invalid", message=error))

    page = spec.get("page") or {}
    width = float(page.get("width", 0))
    height = float(page.get("height", 0))
    elements = spec.get("elements") or []

    allowed_colors = set(design["palette"].values())
    allowed_fonts = set(design["type"][key] for key in ("quote_font", "attribution_font", "source_font"))
    safe_zone = recipe.get("safe_zone") or {}
    sx = float(safe_zone.get("x", 0))
    sy = float(safe_zone.get("y", 0))
    sw = float(safe_zone.get("width", width))
    sh = float(safe_zone.get("height", height))

    expected_quote = content.get("quote", "").strip()
    expected_author = f"— {content.get('author', '').strip()}".strip()
    expected_source = content.get("source", "").strip()

    for index, element in enumerate(elements):
        element_type = element.get("type")
        color_fields = [field for field in ("fill", "stroke") if field in element and element.get(field) is not None]
        for field in color_fields:
            value = element[field]
            if isinstance(value, str):
                if not HEX_COLOR_RE.match(value):
                    issues.append(LintIssue(code="color.invalid", message=f"elements[{index}].{field} uses invalid color {value}", element_index=index))
                elif value not in allowed_colors:
                    issues.append(LintIssue(code="color.unknown", message=f"elements[{index}].{field} references non-design color {value}", element_index=index))

        if element_type == "text":
            font = element.get("font")
            if isinstance(font, str) and font not in allowed_fonts:
                issues.append(LintIssue(code="font.unknown", message=f"elements[{index}].font references non-design font {font}", element_index=index))
            text = str(element.get("text", ""))
            if text == expected_quote and not _text_required_present(text):
                issues.append(LintIssue(code="recipe.quote_missing", message="quote text is empty", element_index=index))
            if text == expected_author and not _text_required_present(text.replace('—', '').strip()):
                issues.append(LintIssue(code="recipe.author_missing", message="author text is empty", element_index=index))
            if text == expected_source and not _text_required_present(text):
                issues.append(LintIssue(code="recipe.source_missing", message="source text is empty", element_index=index))

        if element_type in {"rect", "oval", "image"}:
            if not _element_within_page(element, width, height):
                issues.append(LintIssue(code="layout.off_page", message=f"elements[{index}] extends beyond page bounds", element_index=index))
        elif element_type == "line":
            if not _line_within_page(element, width, height):
                issues.append(LintIssue(code="layout.off_page", message=f"elements[{index}] extends beyond page bounds", element_index=index))

        if element_type == "image":
            image_path = Path(str(element.get("path", "")))
            if not image_path.exists():
                issues.append(LintIssue(code="asset.missing", message=f"image asset not found: {element.get('path')}", element_index=index))

    placements = recipe.get("placements") or {}
    panel = placements.get("panel") or {}
    accent = placements.get("accent_bar") or {}
    if elements:
        if len(elements) < 1 or elements[0].get("type") != "rect" or not _matches_geometry(elements[0], panel):
            issues.append(LintIssue(code="recipe.panel_mismatch", message="first element must match panel placement"))
        if len(elements) < 2 or elements[1].get("type") != "rect" or not _accent_bar_valid(elements[1], accent, panel):
            issues.append(LintIssue(code="recipe.accent_bar_mismatch", message="accent bar must stay inside panel and honor recipe edge"))

    if sx < 0 or sy < 0 or sx + sw > width or sy + sh > height:
        issues.append(LintIssue(code="recipe.safe_zone_invalid", message="safe_zone does not fit inside page"))

    return issues


def _lint_payload(issues: list[LintIssue]) -> dict[str, Any]:
    errors = [issue for issue in issues if issue.level == "error"]
    warnings = [issue for issue in issues if issue.level == "warning"]
    return {
        "ok": not errors,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "issues": [
            {
                "code": issue.code,
                "level": issue.level,
                "message": issue.message,
                **({"element_index": issue.element_index} if issue.element_index is not None else {}),
            }
            for issue in issues
        ],
    }


def _element_within_page(element: dict[str, Any], width: float, height: float) -> bool:
    x = float(element.get("x", 0))
    y = float(element.get("y", 0))
    w = float(element.get("width", 0))
    h = float(element.get("height", 0))
    return x >= 0 and y >= 0 and w >= 0 and h >= 0 and x + w <= width and y + h <= height


def _line_within_page(element: dict[str, Any], width: float, height: float) -> bool:
    points = [(float(element.get("x1", 0)), float(element.get("y1", 0))), (float(element.get("x2", 0)), float(element.get("y2", 0)))]
    return all(0 <= x <= width and 0 <= y <= height for x, y in points)


def _text_required_present(value: str) -> bool:
    return bool(value.strip())


def _matches_geometry(element: dict[str, Any], placement: dict[str, Any]) -> bool:
    return all(round(float(element.get(field, -1)), 3) == round(float(placement.get(field, -2)), 3) for field in ("x", "y", "width", "height"))


def _accent_bar_valid(element: dict[str, Any], placement: dict[str, Any], panel: dict[str, Any]) -> bool:
    x = float(element.get("x", -1))
    y = float(element.get("y", -1))
    width = float(element.get("width", -1))
    height = float(element.get("height", -1))
    panel_x = float(panel.get("x", -2))
    panel_y = float(panel.get("y", -2))
    panel_w = float(panel.get("width", -2))
    panel_h = float(panel.get("height", -2))
    baseline_y = float(placement.get("y", panel_y))
    return (
        height > 0
        and width > 0
        and x >= panel_x
        and y >= panel_y
        and x + width <= panel_x + panel_w
        and y + height <= panel_y + panel_h
        and abs(y - baseline_y) <= 48
    )


def _layout_name(index: int) -> str:
    return ["balanced", "top-heavy", "middle-stack", "lower-anchor"][index % 4]
