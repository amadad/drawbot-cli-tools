"""Shared DrawBot backend resolution and proxy helpers.

Backend precedence contract:
1. Explicit CLI or function selection
2. DRAWBOT_BACKEND environment variable
3. Auto-detect (prefer native drawBot, then drawbot_skia.drawbot)

This module centralizes backend selection so CLI-owned flows can consistently
use either native macOS DrawBot or drawbot-skia.
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from types import ModuleType
from typing import Dict, Optional

DRAWBOT_BACKEND_ENV_VAR = "DRAWBOT_BACKEND"
NATIVE_BACKEND = "drawbot"
SKIA_BACKEND = "drawbot-skia"
SUPPORTED_BACKENDS = (NATIVE_BACKEND, SKIA_BACKEND)

_BACKEND_IMPORTS = {
    NATIVE_BACKEND: "drawBot",
    SKIA_BACKEND: "drawbot_skia.drawbot",
}

_BACKEND_LABELS = {
    NATIVE_BACKEND: "native DrawBot",
    SKIA_BACKEND: "drawbot-skia",
}

_INSTALL_GUIDANCE = {
    NATIVE_BACKEND: "Install native DrawBot with: uv sync --extra drawbot",
    SKIA_BACKEND: "Install drawbot-skia with: uv sync --extra drawbot-skia",
}


@dataclass(frozen=True)
class BackendInfo:
    """Resolved backend metadata."""

    name: str
    module_name: str
    display_name: str
    source: str


class DrawBotBackendError(RuntimeError):
    """Raised when backend resolution or loading fails."""


_backend_cache: Dict[str, ModuleType] = {}
_resolved_backend_cache: Optional[tuple[BackendInfo, ModuleType]] = None


def normalize_backend_name(name: Optional[str]) -> Optional[str]:
    """Normalize a backend selector to a supported canonical name."""
    if name is None:
        return None

    normalized = name.strip().lower()
    aliases = {
        "native": NATIVE_BACKEND,
        "native-drawbot": NATIVE_BACKEND,
        "drawbot": NATIVE_BACKEND,
        "skia": SKIA_BACKEND,
        "drawbot-skia": SKIA_BACKEND,
        "drawbot_skia": SKIA_BACKEND,
    }
    return aliases.get(normalized, normalized)


def validate_backend_name(name: Optional[str]) -> Optional[str]:
    """Validate a backend selector and return its canonical name."""
    normalized = normalize_backend_name(name)
    if normalized is None:
        return None
    if normalized not in SUPPORTED_BACKENDS:
        supported = ", ".join(SUPPORTED_BACKENDS)
        raise DrawBotBackendError(
            f"Unsupported DrawBot backend '{name}'. Supported backends: {supported}. "
            f"Set {DRAWBOT_BACKEND_ENV_VAR} or pass --backend with one of those values."
        )
    return normalized


def backend_metadata(name: str, source: str) -> BackendInfo:
    canonical = validate_backend_name(name)
    assert canonical is not None
    return BackendInfo(
        name=canonical,
        module_name=_BACKEND_IMPORTS[canonical],
        display_name=_BACKEND_LABELS[canonical],
        source=source,
    )


def _load_backend_module(name: str) -> ModuleType:
    canonical = validate_backend_name(name)
    assert canonical is not None

    if canonical in _backend_cache:
        return _backend_cache[canonical]

    try:
        module = importlib.import_module(_BACKEND_IMPORTS[canonical])
    except ImportError as exc:
        raise DrawBotBackendError(
            f"Could not import {_BACKEND_LABELS[canonical]} backend '{canonical}'. "
            f"{_INSTALL_GUIDANCE[canonical]}"
        ) from exc

    _backend_cache[canonical] = module
    return module


def autodetect_backend() -> Optional[BackendInfo]:
    """Auto-detect an installed backend, preferring native DrawBot first."""
    for name in (NATIVE_BACKEND, SKIA_BACKEND):
        try:
            _load_backend_module(name)
            return backend_metadata(name, source="auto")
        except DrawBotBackendError:
            continue
    return None


def resolve_backend(selected: Optional[str] = None, env: Optional[dict] = None) -> BackendInfo:
    """Resolve backend metadata using explicit > env > auto precedence."""
    environment = os.environ if env is None else env

    explicit = validate_backend_name(selected)
    if explicit:
        _load_backend_module(explicit)
        return backend_metadata(explicit, source="explicit")

    env_name = validate_backend_name(environment.get(DRAWBOT_BACKEND_ENV_VAR))
    if env_name:
        _load_backend_module(env_name)
        return backend_metadata(env_name, source="env")

    autodetected = autodetect_backend()
    if autodetected is not None:
        return autodetected

    raise DrawBotBackendError(
        "No supported DrawBot backend is installed. "
        "Install native DrawBot on macOS with 'uv sync --extra drawbot' "
        "or install the cross-platform backend with 'uv sync --extra drawbot-skia'. "
        "Image compatibility relies on Pillow, which is already included in this project."
    )


def get_backend(selected: Optional[str] = None, env: Optional[dict] = None) -> ModuleType:
    """Resolve and import the active DrawBot backend module."""
    info = resolve_backend(selected=selected, env=env)
    return _load_backend_module(info.name)


def get_resolved_backend(selected: Optional[str] = None, env: Optional[dict] = None) -> tuple[BackendInfo, ModuleType]:
    """Return resolved backend metadata and module."""
    global _resolved_backend_cache
    if selected is None and env is None and _resolved_backend_cache is not None:
        return _resolved_backend_cache

    info = resolve_backend(selected=selected, env=env)
    module = _load_backend_module(info.name)
    if selected is None and env is None:
        _resolved_backend_cache = (info, module)
    return info, module


class _DrawBotProxy:
    """Lazy proxy to the resolved backend module."""

    def __getattr__(self, name: str):
        module = get_backend()
        return getattr(module, name)


db = _DrawBotProxy()


__all__ = [
    "BackendInfo",
    "DRAWBOT_BACKEND_ENV_VAR",
    "DrawBotBackendError",
    "NATIVE_BACKEND",
    "SKIA_BACKEND",
    "SUPPORTED_BACKENDS",
    "autodetect_backend",
    "backend_metadata",
    "db",
    "get_backend",
    "get_resolved_backend",
    "normalize_backend_name",
    "resolve_backend",
    "validate_backend_name",
]
