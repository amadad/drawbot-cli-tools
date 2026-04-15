from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

SOCIAL_QUOTE_PAGE = (1080, 1350)
SOCIAL_QUOTE_RATIO = "4:5"
SOCIAL_QUOTE_REQUIRED_FIELDS = ["quote", "author", "source"]
SOCIAL_QUOTE_ALLOWED_PLACEMENTS = ["quote", "author", "source", "accent_bar", "panel"]
SOCIAL_QUOTE_VARIANTS = {
    "accent_edge": ["bottom"],
    "format": ["social-quote-portrait"],
}
SOCIAL_QUOTE_EMBEDDED_TEXT_ORDER = ("quote", "author", "source")


def load_recipe(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("Top-level recipe must be a mapping.")
    return data


def _load_content(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("Top-level content must be a mapping.")
    return data


def _number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def validate_recipe(recipe: dict[str, Any], recipe_path: Path | None = None) -> list[str]:
    errors: list[str] = []
    content: dict[str, Any] | None = None

    if recipe.get("contract_version") != 1:
        errors.append("contract_version must be 1")
    if recipe.get("artifact") != "social-quote":
        errors.append("artifact must be social-quote")
    if recipe.get("brand") != "acme":
        errors.append("brand must be acme")

    page = recipe.get("page")
    if not isinstance(page, dict):
        errors.append("page must be a mapping")
        page = {}

    width = _number(page.get("width"))
    height = _number(page.get("height"))
    if width is None or height is None:
        errors.append("page.width and page.height must be numbers")
    elif (int(width), int(height)) != SOCIAL_QUOTE_PAGE:
        errors.append("page must be 1080x1350 for social-quote")

    safe_zone = recipe.get("safe_zone")
    if not isinstance(safe_zone, dict):
        errors.append("safe_zone must be a mapping")
        safe_zone = {}

    for field in ("x", "y", "width", "height"):
        if _number(safe_zone.get(field)) is None:
            errors.append(f"safe_zone.{field} must be a number")

    if width is not None and height is not None:
        sx = _number(safe_zone.get("x"))
        sy = _number(safe_zone.get("y"))
        sw = _number(safe_zone.get("width"))
        sh = _number(safe_zone.get("height"))
        if None not in (sx, sy, sw, sh):
            if sx < 0 or sy < 0 or sw <= 0 or sh <= 0:
                errors.append("safe_zone geometry must be positive and non-negative")
            elif sx + sw > width or sy + sh > height:
                errors.append("safe_zone must fit inside the page")

    placements = recipe.get("placements")
    if not isinstance(placements, dict):
        errors.append("placements must be a mapping")
        placements = {}

    sx = _number(safe_zone.get("x"))
    sy = _number(safe_zone.get("y"))
    sw = _number(safe_zone.get("width"))
    sh = _number(safe_zone.get("height"))
    for name, placement in placements.items():
        if name not in SOCIAL_QUOTE_ALLOWED_PLACEMENTS:
            errors.append(f"placements.{name} is not allowed for social-quote")
            continue
        if not isinstance(placement, dict):
            errors.append(f"placements.{name} must be a mapping")
            continue
        for field in ("x", "y", "width", "height"):
            value = _number(placement.get(field))
            if value is None:
                errors.append(f"placements.{name}.{field} must be a number")
        if placement.get("anchor") not in {"bottom-left", "top-left"}:
            errors.append(f"placements.{name}.anchor must be bottom-left or top-left")

        px = _number(placement.get("x"))
        py = _number(placement.get("y"))
        pw = _number(placement.get("width"))
        ph = _number(placement.get("height"))
        if None not in (sx, sy, sw, sh, px, py, pw, ph):
            if px < sx or py < sy or px + pw > sx + sw or py + ph > sy + sh:
                errors.append(f"placements.{name} must fit inside safe_zone")

    variants = recipe.get("variants")
    if not isinstance(variants, dict):
        errors.append("variants must be a mapping")
        variants = {}

    for key, allowed in SOCIAL_QUOTE_VARIANTS.items():
        if variants.get(key) not in allowed:
            errors.append(f"variants.{key} must be one of: {', '.join(allowed)}")

    content_ref = recipe.get("content")
    if not isinstance(content_ref, str) or not content_ref:
        errors.append("content must be a non-empty path string")
    elif recipe_path is not None:
        content_path = Path(content_ref)
        if not content_path.is_absolute():
            candidates = [recipe_path.parent / content_path, Path.cwd() / content_path]
            content_path = next((candidate for candidate in candidates if candidate.exists()), candidates[0])
        if not content_path.exists():
            errors.append(f"content file not found: {content_ref}")
        else:
            try:
                content = _load_content(content_path)
            except ValueError as exc:
                errors.append(str(exc))
            else:
                for field in SOCIAL_QUOTE_REQUIRED_FIELDS:
                    value = content.get(field)
                    if not isinstance(value, str) or not value.strip():
                        errors.append(f"content missing required field: {field}")

    if content is not None:
        embedded = _embedded_content(recipe)
        for field in SOCIAL_QUOTE_REQUIRED_FIELDS:
            expected = content.get(field)
            actual = embedded.get(field)
            if isinstance(expected, str) and expected.strip() and actual != expected:
                errors.append(f"embedded {field} must match content fixture")

    return errors


def _embedded_content(recipe: dict[str, Any]) -> dict[str, str | None]:
    elements = recipe.get("elements")
    texts: list[str] = []
    if isinstance(elements, list):
        for element in elements:
            if isinstance(element, dict) and element.get("type") == "text" and isinstance(element.get("text"), str):
                texts.append(element["text"])

    return {
        field: texts[index] if index < len(texts) else None
        for index, field in enumerate(SOCIAL_QUOTE_EMBEDDED_TEXT_ORDER)
    }


def explain_recipe(recipe: dict[str, Any]) -> dict[str, Any]:
    page = recipe.get("page") or {}
    safe_zone = recipe.get("safe_zone") or {}
    placements = recipe.get("placements") or {}
    variants = recipe.get("variants") or {}
    return {
        "artifact": recipe.get("artifact"),
        "brand": recipe.get("brand"),
        "page": {
            "width": page.get("width"),
            "height": page.get("height"),
            "aspect_ratio": SOCIAL_QUOTE_RATIO,
        },
        "content_fields": list(SOCIAL_QUOTE_REQUIRED_FIELDS),
        "safe_zone": {
            "x": safe_zone.get("x"),
            "y": safe_zone.get("y"),
            "width": safe_zone.get("width"),
            "height": safe_zone.get("height"),
        },
        "placements": sorted(name for name in placements if name in SOCIAL_QUOTE_ALLOWED_PLACEMENTS),
        "variants": {key: variants.get(key) for key in sorted(SOCIAL_QUOTE_VARIANTS)},
    }
