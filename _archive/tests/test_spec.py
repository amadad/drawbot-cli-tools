from __future__ import annotations

import sys
import types
from contextlib import contextmanager
from pathlib import Path

from PIL import Image

from cli import spec as spec_mod


class FakeBezierPath:
    def __init__(self):
        self.commands = []

    def moveTo(self, point):
        self.commands.append(("moveTo", point))

    def lineTo(self, point):
        self.commands.append(("lineTo", point))

    def curveTo(self, *points):
        self.commands.append(("curveTo", points))

    def closePath(self):
        self.commands.append(("closePath",))

    def rect(self, x, y, width, height):
        self.commands.append(("rect", x, y, width, height))


class FakeBackend:
    BezierPath = FakeBezierPath

    def __init__(self):
        self.operations = []

    @contextmanager
    def savedState(self):
        self.operations.append(("savedState.enter",))
        try:
            yield
        finally:
            self.operations.append(("savedState.exit",))

    def newPage(self, width, height):
        self.operations.append(("newPage", width, height))

    def width(self):
        return 600

    def height(self):
        return 800

    def fill(self, *args):
        self.operations.append(("fill", args))

    def stroke(self, *args):
        self.operations.append(("stroke", args))

    def strokeWidth(self, width):
        self.operations.append(("strokeWidth", width))

    def rect(self, x, y, width, height):
        self.operations.append(("rect", x, y, width, height))

    def oval(self, x, y, width, height):
        self.operations.append(("oval", x, y, width, height))

    def drawPath(self, path):
        self.operations.append(("drawPath", path.commands))

    def clipPath(self, path):
        self.operations.append(("clipPath", path.commands))

    def translate(self, x, y):
        self.operations.append(("translate", x, y))

    def scale(self, x, y=None):
        self.operations.append(("scale", x, x if y is None else y))

    def image(self, path, position):
        self.operations.append(("image", path, position))

    def opacity(self, value):
        self.operations.append(("opacity", value))

    def font(self, name):
        self.operations.append(("font", name))

    def fontSize(self, size):
        self.operations.append(("fontSize", size))

    def textSize(self, text):
        return (len(text) * 10, 12)

    def text(self, text, position):
        self.operations.append(("text", text, position))

    def line(self, start, end):
        self.operations.append(("line", start, end))

    def saveImage(self, path):
        self.operations.append(("saveImage", path))


class FakeGrid:
    def __init__(self, cell_width=100, cell_height=50):
        self.cell_width = cell_width
        self.cell_height = cell_height

    @classmethod
    def from_margins(cls, margins, column_subdivisions=12, row_subdivisions=8):
        return cls()

    def __getitem__(self, key):
        col, row = key
        return (col * self.cell_width, row * self.cell_height)

    def __mul__(self, key):
        cols, rows = key
        return (cols * self.cell_width, rows * self.cell_height)


class FakeScale:
    title = 72
    h1 = 48
    h2 = 36
    h3 = 24
    body = 12
    caption = 10


def install_render_stubs(monkeypatch, backend):
    monkeypatch.setitem(
        sys.modules,
        "drawbot_backend",
        types.SimpleNamespace(get_backend=lambda selected=None: backend),
    )
    monkeypatch.setitem(
        sys.modules,
        "drawbot_design_system",
        types.SimpleNamespace(
            BOOK_SCALE=FakeScale(),
            MAGAZINE_SCALE=FakeScale(),
            POSTER_SCALE=FakeScale(),
            REPORT_SCALE=FakeScale(),
            draw_wrapped_text=lambda *args, **kwargs: None,
            get_output_path=lambda name: Path("/tmp") / name,
            setup_poster_page=lambda page_format: (600, 800, 72),
        ),
    )
    monkeypatch.setitem(sys.modules, "drawbot_grid", types.SimpleNamespace(Grid=FakeGrid))


def test_build_rounded_rect_path_uses_curve_segments_without_backend_helper():
    backend = FakeBackend()

    path = spec_mod.build_rounded_rect_path(backend, 10, 20, 120, 80, 12)

    assert any(command[0] == "curveTo" for command in path.commands)
    assert path.commands[0] == ("moveTo", (22, 20))


def test_compute_image_placement_supports_fit_fill_and_stretch():
    frame = (10, 20, 100, 100)
    intrinsic = (200, 100)

    fit = spec_mod.compute_image_placement(frame, intrinsic, "fit")
    fill = spec_mod.compute_image_placement(frame, intrinsic, "fill")
    stretch = spec_mod.compute_image_placement(frame, intrinsic, "stretch")

    assert fit == (10, 45, 0.5, 0.5)
    assert fill == (-40, 20, 1.0, 1.0)
    assert stretch == (10, 20, 0.5, 1.0)


def test_render_from_spec_uses_backend_safe_rect_and_image_logic(tmp_path, monkeypatch):
    backend = FakeBackend()
    install_render_stubs(monkeypatch, backend)

    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    image_path = assets_dir / "photo.png"
    Image.new("RGB", (200, 100), color="red").save(image_path)

    spec_path = tmp_path / "poster.yaml"
    spec_path.write_text(
        """
page:
  format: letter
  margins: 0

elements:
  - type: rect
    grid: [0, 0, 2, 2]
    fill: "#112233"
    corner_radius: 16

  - type: image
    path: assets/photo.png
    grid: [1, 1, 1, 2]
    fit: fill
    opacity: 0.4
""".strip(),
        encoding="utf-8",
    )

    output_path = tmp_path / "poster.pdf"
    result = spec_mod.render_from_spec(spec_path, output_path=output_path, backend="drawbot-skia")

    assert result == output_path
    assert not any(op[0] == "roundedRect" for op in backend.operations)
    assert not any(op[0] == "imageSize" for op in backend.operations)

    draw_path_ops = [op for op in backend.operations if op[0] == "drawPath"]
    assert draw_path_ops, "rounded rect should be rendered via drawPath(path)"
    assert any(cmd[0] == "curveTo" for cmd in draw_path_ops[0][1])

    assert ("opacity", 0.4) in backend.operations
    assert any(op[0] == "clipPath" for op in backend.operations), "fill images should clip to frame"
    assert ("translate", 50.0, 50.0) in backend.operations
    assert ("scale", 1.0, 1.0) in backend.operations
    assert any(op[0] == "image" and op[1].endswith("assets/photo.png") for op in backend.operations)
    assert ("saveImage", str(output_path)) in backend.operations
