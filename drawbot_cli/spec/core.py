from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from drawbot_cli.runtime import skia

PAGE_FORMATS: dict[str, tuple[int, int]] = {
    "letter": (612, 792),
    "a4": (595, 842),
    "tabloid": (792, 1224),
    "square": (792, 792),
}


def load_spec(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("Top-level spec must be a mapping.")
    return data


def _as_color(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return (float(value),) * 3
    if isinstance(value, str):
        color = value.lstrip("#")
        if len(color) == 6:
            return tuple(int(color[i : i + 2], 16) / 255 for i in (0, 2, 4))
        raise ValueError(f"Unsupported color string: {value}")
    if isinstance(value, (list, tuple)) and len(value) in (3, 4):
        return tuple(float(channel) for channel in value)
    raise ValueError(f"Unsupported color value: {value!r}")


def _page_size(spec: dict[str, Any]) -> tuple[int, int]:
    page = spec.get("page", {}) or {}
    if "width" in page and "height" in page:
        return int(page["width"]), int(page["height"])

    fmt = page.get("format", "letter")
    if fmt not in PAGE_FORMATS:
        raise ValueError(f"Unknown page format: {fmt}")
    return PAGE_FORMATS[fmt]


def validate_spec(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        _page_size(spec)
    except ValueError as exc:
        errors.append(str(exc))

    elements = spec.get("elements", [])
    if not isinstance(elements, list):
        errors.append("elements must be a list")
        return errors

    for index, element in enumerate(elements):
        if not isinstance(element, dict):
            errors.append(f"elements[{index}] must be a mapping")
            continue
        if "type" not in element:
            errors.append(f"elements[{index}] is missing type")
            continue

        element_type = element["type"]
        if element_type in {"rect", "oval"}:
            for field in ("x", "y", "width", "height"):
                if field not in element:
                    errors.append(f"elements[{index}] missing {field}")
        elif element_type == "line":
            for field in ("x1", "y1", "x2", "y2"):
                if field not in element:
                    errors.append(f"elements[{index}] missing {field}")
        elif element_type == "text":
            for field in ("text", "x", "y"):
                if field not in element:
                    errors.append(f"elements[{index}] missing {field}")
        elif element_type == "image":
            for field in ("path", "x", "y"):
                if field not in element:
                    errors.append(f"elements[{index}] missing {field}")
        else:
            errors.append(f"elements[{index}] has unsupported type {element_type}")

    return errors


def explain_spec(spec: dict[str, Any]) -> dict[str, Any]:
    width, height = _page_size(spec)
    elements = spec.get("elements", []) or []
    return {
        "page": {"width": width, "height": height},
        "element_count": len(elements),
        "element_types": [element.get("type", "?") for element in elements if isinstance(element, dict)],
        "output": spec.get("output"),
    }


def _set_paint(db, fill_value, stroke_value, stroke_width):
    fill = _as_color(fill_value)
    stroke = _as_color(stroke_value)

    if fill is None:
        db.fill(None)
    else:
        db.fill(*fill)

    if stroke is None:
        db.stroke(None)
    else:
        db.stroke(*stroke)
        db.strokeWidth(float(stroke_width or 1.0))


def render_spec(path: Path, output: Path | None = None) -> Path:
    spec = load_spec(path)
    errors = validate_spec(spec)
    if errors:
        raise ValueError("; ".join(errors))

    db = skia.get_drawbot_module()
    width, height = _page_size(spec)
    output_path = output or path.with_suffix(".pdf")

    db.newDrawing()
    try:
        db.newPage(width, height)

        page = spec.get("page", {}) or {}
        background = page.get("background")
        if background is not None:
            background_color = _as_color(background)
            if background_color is None:
                raise ValueError("page.background cannot be null")
            db.fill(*background_color)
            db.stroke(None)
            db.rect(0, 0, width, height)

        for element in spec.get("elements", []) or []:
            element_type = element["type"]
            if element_type == "rect":
                _set_paint(db, element.get("fill", 0), element.get("stroke"), element.get("stroke_width", 1.0))
                db.rect(float(element["x"]), float(element["y"]), float(element["width"]), float(element["height"]))
            elif element_type == "oval":
                _set_paint(db, element.get("fill", 0), element.get("stroke"), element.get("stroke_width", 1.0))
                db.oval(float(element["x"]), float(element["y"]), float(element["width"]), float(element["height"]))
            elif element_type == "line":
                db.fill(None)
                stroke = _as_color(element.get("stroke", 0))
                if stroke is None:
                    raise ValueError("line.stroke cannot be null")
                db.stroke(*stroke)
                db.strokeWidth(float(element.get("stroke_width", 1.0)))
                db.line((float(element["x1"]), float(element["y1"])), (float(element["x2"]), float(element["y2"])))
            elif element_type == "text":
                fill = _as_color(element.get("fill", 0))
                if fill is None:
                    raise ValueError("text.fill cannot be null")
                db.fill(*fill)
                db.stroke(None)
                db.font(element.get("font", "Helvetica"))
                db.fontSize(float(element.get("font_size", 12)))
                db.text(str(element["text"]), (float(element["x"]), float(element["y"])))
            elif element_type == "image":
                image_path = Path(element["path"])
                if not image_path.is_absolute():
                    image_path = path.parent / image_path
                db.image(str(image_path), (float(element["x"]), float(element["y"])))

        db.saveImage(str(output_path))
    finally:
        db.endDrawing()

    return output_path.resolve()
