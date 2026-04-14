import random
from pathlib import Path

import pytest

from cli import evolve as evolve_mod
from cli.evolve import genome as genome_mod
from cli.evolve import render as render_mod
from cli.evolve import semantics as semantics_mod
from cli.evolve import server as server_mod
from cli.evolve.generators import layered_form as layered_form_mod


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

    def oval(self, x, y, width, height):
        self.commands.append(("oval", x, y, width, height))

    def union(self, other):
        merged = FakeBezierPath()
        merged.commands = self.commands + other.commands
        return merged

    def bounds(self):
        return (0, 0, 100, 100)

    def pointInside(self, point):
        return True

    def pointOnContour(self, contour, t):
        return (t * 100, t * 100)


class FakeDrawBot:
    BezierPath = FakeBezierPath


def test_concept_to_style_uses_monochrome_form_language():
    style = semantics_mod.concept_to_style(semantics_mod.CONCEPTS["chaos"])

    assert style["fill_color"] == [0.0, 0.0, 0.0]
    assert style["background"] == [1.0, 1.0, 1.0]
    assert style["stroke_color"] == [0.0, 0.0, 0.0]
    assert style["_gravity"] == "scatter"
    assert style["_ink_mode"] == "echo"
    assert style["_accent_scale"] > 1.0


def test_build_generation_style_normalizes_legacy_color_defaults():
    style = evolve_mod.build_generation_style(
        {
            "style": {
                "fill_color": [0.9, 0.4, 0.7],
                "stroke_color": None,
                "stroke_width": 0,
            }
        }
    )

    assert style["fill_color"] == [0.0, 0.0, 0.0]
    assert style["stroke_color"] == [0.0, 0.0, 0.0]
    assert style["stroke_width"] == pytest.approx(0.8)


def test_list_demo_generators_skips_support_only_generators():
    demo_generators = evolve_mod.list_demo_generators()

    assert "layered_form" in demo_generators
    assert "soft_blob" in demo_generators
    assert "accent_nodes" not in demo_generators
    assert "dot_field" not in demo_generators


def test_resolve_render_plan_applies_semantic_position_and_scale():
    genome = genome_mod.FormGenome(
        id="gen000_0001",
        generator="soft_blob",
        params={"roundness": 0.5},
        seed=123,
    )

    bottom = render_mod.resolve_render_plan(
        genome,
        (200, 200),
        {"_gravity": "bottom", "_scale": 0.6},
    )
    scatter_a = render_mod.resolve_render_plan(
        genome,
        (200, 200),
        {"_gravity": "scatter", "_scale": 0.8},
    )
    scatter_b = render_mod.resolve_render_plan(
        genome,
        (200, 200),
        {"_gravity": "scatter", "_scale": 0.8},
    )

    assert bottom["center"][1] == pytest.approx(76.0)
    assert bottom["size"] == pytest.approx(120.0)
    assert scatter_a == scatter_b
    assert scatter_a["center"] != (100.0, 100.0)


def test_layered_form_rounded_rect_does_not_require_drawbot_helper(monkeypatch):
    monkeypatch.setattr(layered_form_mod, "_db", FakeDrawBot())

    path = layered_form_mod._generate_base_shape(
        "rounded_rect",
        center=(100, 100),
        size=160,
        params={
            "roundness": 0.75,
            "aspect": 1.0,
            "asymmetry": 0.1,
            "lobe_count": 4,
        },
        rng=random.Random(0),
    )

    assert isinstance(path, FakeBezierPath)
    assert any(command[0] == "curveTo" for command in path.commands)


def test_layered_form_builds_carved_structural_layers(monkeypatch):
    monkeypatch.setattr(layered_form_mod, "_db", FakeDrawBot())

    genome = genome_mod.FormGenome(
        id="gen000_0001",
        generator="layered_form",
        params={
            "shape_type": 0.5,
            "roundness": 0.8,
            "aspect": 0.6,
            "lobe_count": 0.8,
            "lobe_depth": 0.45,
            "asymmetry": 0.7,
            "dot_density": 0.8,
            "accent_count": 0.6,
        },
        seed=7,
    )

    form = layered_form_mod.generate_layered_form(genome, (100, 100), 160)
    layer_names = [layer["name"] for layer in form["layers"]]

    assert layer_names.count("fill") >= 2
    assert "carve" in layer_names
    assert layer_names[-1] == "outline"


def test_generation_detail_includes_actual_params_and_parent_deltas(
    monkeypatch, tmp_path
):
    generations_dir = tmp_path / "generations"

    def generation_dir(gen_num: int) -> Path:
        return generations_dir / f"gen_{gen_num:03d}"

    gen0_dir = generation_dir(0)
    gen1_dir = generation_dir(1)
    (gen0_dir / "candidates").mkdir(parents=True)
    (gen1_dir / "candidates").mkdir(parents=True)
    (gen1_dir / "candidates" / "0001.svg").write_text("<svg/>")

    parent_a = genome_mod.FormGenome(
        id="gen000_0001",
        generator="soft_blob",
        params={"roundness": 0.4},
        seed=1,
        prompt="soft",
    )
    parent_b = genome_mod.FormGenome(
        id="gen000_0002",
        generator="soft_blob",
        params={"roundness": 0.6},
        seed=2,
        prompt="soft",
    )
    child = genome_mod.FormGenome(
        id="gen001_0001",
        generator="soft_blob",
        params={"roundness": 0.8},
        seed=3,
        parents=(parent_a.id, parent_b.id),
        prompt="soft",
        concept="stillness",
    )

    genome_mod.save_population([parent_a, parent_b], gen0_dir / "population.jsonl")
    genome_mod.save_population([child], gen1_dir / "population.jsonl")

    monkeypatch.setattr(server_mod, "get_generation_dir", generation_dir)

    detail = server_mod._generation_detail(1)

    assert detail is not None
    assert detail["settings"]["generator"] == "soft_blob"
    assert detail["settings"]["prompt"] == "soft"
    candidate = detail["candidates"][0]
    assert candidate["actual_params"]["roundness"] == pytest.approx(0.8)
    assert candidate["parent_deltas"]["roundness"] == pytest.approx(0.3)
    assert candidate["has_svg"] is True
