import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

import drawbot_backend as backend


class MockGridDrawBot:
    def __init__(self, width=200, height=100, *, fail=False):
        self._width = width
        self._height = height
        self._fail = fail

    def width(self):
        if self._fail:
            raise RuntimeError("no active canvas")
        return self._width

    def height(self):
        if self._fail:
            raise RuntimeError("no active canvas")
        return self._height


@pytest.fixture(autouse=True)
def reset_backend_state(monkeypatch):
    backend._backend_cache.clear()
    backend._resolved_backend_cache = None
    monkeypatch.delenv(backend.DRAWBOT_BACKEND_ENV_VAR, raising=False)


@pytest.fixture
def reload_grid_module():
    if "drawbot_grid" in sys.modules:
        del sys.modules["drawbot_grid"]
    import drawbot_grid as grid_module

    return grid_module


def test_grid_from_margins_uses_backend_page_size(reload_grid_module):
    backend._backend_cache[backend.NATIVE_BACKEND] = MockGridDrawBot(width=200, height=100)
    grid_module = reload_grid_module

    grid = grid_module.Grid.from_margins(
        (-10, -20, -10, -20),
        column_subdivisions=2,
        row_subdivisions=2,
        column_gutter=0,
        row_gutter=0,
    )

    assert (grid.x, grid.y, grid.width, grid.height) == (10, 20, 180, 60)
    assert grid[(1, 1)] == (100, 50)
    assert grid * (2, 2) == (180, 60)


def test_grid_from_margins_falls_back_to_letter_without_active_canvas(reload_grid_module):
    backend._backend_cache[backend.NATIVE_BACKEND] = MockGridDrawBot(fail=True)
    grid_module = reload_grid_module

    grid = grid_module.Grid.from_margins(
        (-10, -10, -10, -10),
        column_subdivisions=1,
        row_subdivisions=1,
        column_gutter=0,
        row_gutter=0,
    )

    assert (grid.x, grid.y, grid.width, grid.height) == (10, 10, 592, 772)
