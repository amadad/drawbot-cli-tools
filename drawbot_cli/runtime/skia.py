from __future__ import annotations

import importlib
import inspect
import sys
from pathlib import Path
from typing import Any, Callable


class DrawbotSkiaUnavailableError(RuntimeError):
    """Raised when the vendored drawbot-skia runtime cannot be imported."""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def vendor_root() -> Path:
    return repo_root() / "vendor"


def vendor_src() -> Path:
    return vendor_root() / "src"


def ensure_vendor_on_path() -> Path:
    src = vendor_src()
    if not src.exists():
        raise DrawbotSkiaUnavailableError(
            f"Vendored drawbot-skia source not found at {src}. Expected vendor/src."
        )

    src_str = str(src)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)
    return src


def _import(module_name: str):
    ensure_vendor_on_path()
    try:
        return importlib.import_module(module_name)
    except Exception as exc:  # noqa: BLE001 - surface the actual dependency/import failure
        raise DrawbotSkiaUnavailableError(
            "Could not import the vendored drawbot-skia runtime. "
            f"Tried module '{module_name}' from {vendor_src()}. "
            f"Underlying error: {exc.__class__.__name__}: {exc}"
        ) from exc


def get_package_module():
    return _import("drawbot_skia")


def get_drawbot_module():
    return _import("drawbot_skia.drawbot")


def get_runner_main() -> Callable[[list[str] | None], None]:
    module = _import("drawbot_skia.__main__")
    return module.main


def get_version() -> str:
    package = get_package_module()
    return getattr(package, "__version__", "0.0.0+unknown")


def list_symbols() -> list[str]:
    module = get_drawbot_module()
    names = getattr(module, "__all__", None)
    if not names:
        names = [name for name in dir(module) if not name.startswith("_")]
    return sorted(set(names))


def describe_symbol(name: str) -> dict[str, Any]:
    module = get_drawbot_module()
    if not hasattr(module, name):
        raise KeyError(name)

    value = getattr(module, name)
    details: dict[str, Any] = {
        "name": name,
        "kind": type(value).__name__,
        "module": getattr(value, "__module__", module.__name__),
        "callable": callable(value),
    }

    if callable(value):
        try:
            details["signature"] = str(inspect.signature(value))
        except (TypeError, ValueError):
            details["signature"] = None
    else:
        details["signature"] = None

    doc = inspect.getdoc(value)
    details["doc"] = doc.splitlines()[0] if doc else None
    return details


def known_gaps() -> list[dict[str, str]]:
    return [
        {
            "feature": "textBox",
            "status": "missing",
            "note": "Called out upstream as a major obstacle; no stable support yet.",
        },
        {
            "feature": "FormattedString",
            "status": "missing",
            "note": "Still on the upstream roadmap; not part of the stable headless surface.",
        },
        {
            "feature": "multi-style text",
            "status": "partial",
            "note": "Single-line text is usable; richer text layout remains incomplete.",
        },
        {
            "feature": "ImageObject",
            "status": "missing",
            "note": "The macOS ImageObject model is not a target for this CLI.",
        },
    ]
