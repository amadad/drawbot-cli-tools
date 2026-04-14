import sys
from pathlib import Path
import types

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

import drawbot_backend as backend


@pytest.fixture(autouse=True)
def reset_backend_state(monkeypatch):
    backend._backend_cache.clear()
    backend._resolved_backend_cache = None
    monkeypatch.delenv(backend.DRAWBOT_BACKEND_ENV_VAR, raising=False)


@pytest.fixture
def fake_imports(monkeypatch):
    modules = {
        "drawBot": types.SimpleNamespace(__name__="drawBot"),
        "drawbot_skia.drawbot": types.SimpleNamespace(__name__="drawbot_skia.drawbot"),
    }
    available = set()

    def fake_import_module(name):
        if name not in available:
            raise ImportError(name)
        return modules[name]

    monkeypatch.setattr(backend.importlib, "import_module", fake_import_module)
    return available, modules


def test_explicit_backend_overrides_env(fake_imports, monkeypatch):
    available, _ = fake_imports
    available.update({"drawBot", "drawbot_skia.drawbot"})
    monkeypatch.setenv(backend.DRAWBOT_BACKEND_ENV_VAR, backend.NATIVE_BACKEND)

    info = backend.resolve_backend(selected=backend.SKIA_BACKEND)

    assert info.name == backend.SKIA_BACKEND
    assert info.source == "explicit"


def test_env_backend_overrides_auto_detect(fake_imports, monkeypatch):
    available, _ = fake_imports
    available.update({"drawBot", "drawbot_skia.drawbot"})
    monkeypatch.setenv(backend.DRAWBOT_BACKEND_ENV_VAR, backend.SKIA_BACKEND)

    info = backend.resolve_backend()

    assert info.name == backend.SKIA_BACKEND
    assert info.source == "env"


def test_auto_detect_prefers_native_drawbot(fake_imports):
    available, _ = fake_imports
    available.update({"drawBot", "drawbot_skia.drawbot"})

    info = backend.resolve_backend()

    assert info.name == backend.NATIVE_BACKEND
    assert info.source == "auto"


def test_auto_detect_falls_back_to_skia(fake_imports):
    available, _ = fake_imports
    available.add("drawbot_skia.drawbot")

    info = backend.resolve_backend()

    assert info.name == backend.SKIA_BACKEND
    assert info.source == "auto"


def test_invalid_backend_name_fails_with_supported_values():
    with pytest.raises(backend.DrawBotBackendError) as exc:
        backend.resolve_backend(selected="banana")

    message = str(exc.value)
    assert "Unsupported DrawBot backend 'banana'" in message
    assert backend.NATIVE_BACKEND in message
    assert backend.SKIA_BACKEND in message


def test_no_backend_installed_has_actionable_install_guidance(fake_imports):
    with pytest.raises(backend.DrawBotBackendError) as exc:
        backend.resolve_backend()

    message = str(exc.value)
    assert "No supported DrawBot backend is installed" in message
    assert "uv sync --extra drawbot" in message
    assert "uv sync --extra drawbot-skia" in message
    assert "Pillow" in message


def test_get_backend_returns_module_for_resolved_backend(fake_imports):
    available, modules = fake_imports
    available.add("drawbot_skia.drawbot")

    resolved = backend.get_backend(selected="skia")

    assert resolved is modules["drawbot_skia.drawbot"]


def test_proxy_uses_resolved_backend_module(fake_imports):
    available, modules = fake_imports
    modules["drawBot"].magic = 42
    available.add("drawBot")

    assert backend.db.magic == 42
