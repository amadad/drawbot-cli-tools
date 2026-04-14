from __future__ import annotations

import json
from typer.testing import CliRunner

from drawbot_cli.app import app
from drawbot_cli.runtime import skia as skia_mod
from drawbot_cli.spec import core as spec_core


runner = CliRunner()


class FakeDB:
    def __init__(self):
        self.ops: list[tuple[object, ...]] = []

    def newDrawing(self):
        self.ops.append(("newDrawing",))

    def newPage(self, width, height):
        self.ops.append(("newPage", width, height))

    def fill(self, *args):
        self.ops.append(("fill", args))

    def stroke(self, *args):
        self.ops.append(("stroke", args))

    def strokeWidth(self, value):
        self.ops.append(("strokeWidth", value))

    def rect(self, x, y, width, height):
        self.ops.append(("rect", x, y, width, height))

    def oval(self, x, y, width, height):
        self.ops.append(("oval", x, y, width, height))

    def line(self, start, end):
        self.ops.append(("line", start, end))

    def font(self, name):
        self.ops.append(("font", name))

    def fontSize(self, size):
        self.ops.append(("fontSize", size))

    def text(self, text, position):
        self.ops.append(("text", text, position))

    def image(self, path, position):
        self.ops.append(("image", path, position))

    def saveImage(self, path):
        self.ops.append(("saveImage", path))

    def endDrawing(self):
        self.ops.append(("endDrawing",))



def test_vendor_paths_match_flat_layout():
    assert skia_mod.vendor_root().name == "vendor"
    assert skia_mod.vendor_src() == skia_mod.vendor_root() / "src"


def test_doctor_reports_vendored_runtime(monkeypatch):
    monkeypatch.setattr(skia_mod, "get_drawbot_module", lambda: type("M", (), {"__name__": "drawbot_skia.drawbot"})())
    monkeypatch.setattr(skia_mod, "get_version", lambda: "1.2.3")

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0, result.stdout
    assert "vendor_root=" in result.stdout
    assert "vendor_src=" in result.stdout
    assert "module=drawbot_skia.drawbot" in result.stdout
    assert "status=ok" in result.stdout


def test_run_passes_script_and_output_to_upstream_runner(tmp_path, monkeypatch):
    script_path = tmp_path / "poster.py"
    script_path.write_text("newPage(100, 100)\nrect(0, 0, 50, 50)\n", encoding="utf-8")
    output_path = tmp_path / "out" / "poster.png"

    captured = {}

    def fake_runner_main(args):
        captured["args"] = args

    monkeypatch.setattr(skia_mod, "get_runner_main", lambda: fake_runner_main)

    result = runner.invoke(app, ["run", str(script_path), "--output", str(output_path)])

    assert result.exit_code == 0, result.stdout
    assert captured["args"] == [str(script_path.resolve()), str(output_path.resolve())]
    assert str(output_path.resolve()) in result.stdout
    assert output_path.parent.exists()


def test_new_writes_minimal_script(tmp_path):
    result = runner.invoke(app, ["new", "hello_poster", "--dir", str(tmp_path)])

    assert result.exit_code == 0, result.stdout
    created = tmp_path / "hello_poster.py"
    assert created.exists()
    text = created.read_text(encoding="utf-8")
    assert "newPage(612, 792)" in text
    assert 'text("Hello Poster"' in text


def test_api_list_outputs_symbols(monkeypatch):
    monkeypatch.setattr(skia_mod, "list_symbols", lambda: ["BezierPath", "newPage", "rect"])

    result = runner.invoke(app, ["api", "list"])

    assert result.exit_code == 0, result.stdout
    assert result.stdout.splitlines() == ["BezierPath", "newPage", "rect"]


def test_api_show_outputs_symbol_details(monkeypatch):
    monkeypatch.setattr(
        skia_mod,
        "describe_symbol",
        lambda name: {
            "name": name,
            "kind": "function",
            "module": "drawbot_skia.drawbot",
            "callable": True,
            "signature": "(width, height)",
            "doc": "Create a new page.",
        },
    )

    result = runner.invoke(app, ["api", "show", "newPage"])

    assert result.exit_code == 0, result.stdout
    assert "name=newPage" in result.stdout
    assert "signature=(width, height)" in result.stdout


def test_api_gaps_can_emit_json():
    result = runner.invoke(app, ["api", "gaps", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert any(item["feature"] == "textBox" for item in payload)


def test_spec_validate_and_explain(tmp_path):
    spec_path = tmp_path / "poster.yaml"
    spec_path.write_text(
        "page:\n  format: letter\nelements:\n  - type: rect\n    x: 10\n    y: 20\n    width: 100\n    height: 50\n",
        encoding="utf-8",
    )

    validate = runner.invoke(app, ["spec", "validate", str(spec_path)])
    explain = runner.invoke(app, ["spec", "explain", str(spec_path), "--json"])

    assert validate.exit_code == 0, validate.stdout
    assert validate.stdout.strip() == "ok"
    explanation = json.loads(explain.stdout)
    assert explanation["page"] == {"width": 612, "height": 792}
    assert explanation["element_count"] == 1
    assert explanation["element_types"] == ["rect"]


def test_spec_render_uses_vendored_runtime(tmp_path, monkeypatch):
    spec_path = tmp_path / "poster.yaml"
    spec_path.write_text(
        "page:\n  width: 200\n  height: 100\n  background: '#ffffff'\nelements:\n  - type: rect\n    x: 0\n    y: 0\n    width: 50\n    height: 20\n    fill: '#000000'\n",
        encoding="utf-8",
    )
    output_path = tmp_path / "poster.pdf"
    fake_db = FakeDB()
    monkeypatch.setattr(skia_mod, "get_drawbot_module", lambda: fake_db)

    result = runner.invoke(app, ["spec", "render", str(spec_path), "-o", str(output_path)])

    assert result.exit_code == 0, result.stdout
    assert result.stdout.strip() == str(output_path.resolve())
    assert ("newPage", 200, 100) in fake_db.ops
    assert ("saveImage", str(output_path.resolve())) in fake_db.ops


def test_spec_core_reports_validation_errors():
    errors = spec_core.validate_spec({"elements": [{"type": "rect", "x": 1}]})
    assert any("missing y" in error for error in errors)
