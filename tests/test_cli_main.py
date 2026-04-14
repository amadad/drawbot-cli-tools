from pathlib import Path

from typer.testing import CliRunner

from cli.main import DRAWBOT_BACKEND_ENV_VAR, app
from cli import main as main_mod


runner = CliRunner()


def test_from_spec_passes_selected_backend_to_repo_owned_renderer(
    tmp_path, monkeypatch
):
    spec_path = tmp_path / "poster.yaml"
    spec_path.write_text("page: {}\nelements: []\n", encoding="utf-8")
    output_path = tmp_path / "poster.pdf"

    captured = {}

    def fake_resolve_backend(selected=None, env=None):
        captured["selected"] = selected
        return type("BackendInfo", (), {"name": "drawbot-skia", "source": "explicit"})()

    def fake_render_from_spec(spec_file, output=None, backend=None, overrides=None):
        captured["spec_file"] = spec_file
        captured["output"] = output
        captured["backend"] = backend
        return output or output_path

    monkeypatch.setattr(main_mod, "resolve_backend", fake_resolve_backend)
    monkeypatch.setattr(main_mod, "_open_file", lambda path: None)
    monkeypatch.setattr("cli.spec.render_from_spec", fake_render_from_spec)

    result = runner.invoke(
        app,
        [
            "from-spec",
            str(spec_path),
            "--output",
            str(output_path),
            "--backend",
            "skia",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert captured["selected"] == "skia"
    assert captured["spec_file"] == spec_path.resolve()
    assert captured["output"] == output_path
    assert captured["backend"] == "drawbot-skia"


def test_render_keeps_default_script_environment_without_backend_selection(
    tmp_path, monkeypatch
):
    script_path = tmp_path / "poster.py"
    script_path.write_text("print('ok')\n", encoding="utf-8")

    calls = []

    def fake_run_drawbot_script(script, output_path=None, backend=None):
        calls.append((script, output_path, backend))
        return True

    monkeypatch.delenv(DRAWBOT_BACKEND_ENV_VAR, raising=False)
    monkeypatch.setattr(main_mod, "run_drawbot_script", fake_run_drawbot_script)

    result = runner.invoke(app, ["render", str(script_path)])

    assert result.exit_code == 0, result.stdout
    assert calls == [(script_path.resolve(), None, None)]


def test_render_propagates_requested_backend_to_wrapper_aware_scripts(
    tmp_path, monkeypatch
):
    script_path = tmp_path / "poster.py"
    script_path.write_text("print('ok')\n", encoding="utf-8")

    calls = []

    def fake_run_drawbot_script(script, output_path=None, backend=None):
        calls.append((script, output_path, backend))
        return True

    monkeypatch.setattr(main_mod, "run_drawbot_script", fake_run_drawbot_script)

    result = runner.invoke(app, ["render", str(script_path), "--backend", "skia"])

    assert result.exit_code == 0, result.stdout
    assert calls == [(script_path.resolve(), None, "drawbot-skia")]
