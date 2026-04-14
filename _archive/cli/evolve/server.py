"""
Web browser for evolutionary form generation.

Serves a gallery UI for viewing candidates, selecting winners, and breeding
new generations — replacing the PDF contact sheet workflow with an interactive
browser-based interface.

Uses only stdlib http.server (no external deps).
"""

import json
import shutil
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import mimetypes

from . import (
    GENERATIONS_DIR,
    DEFAULT_CONFIG,
    build_generation_style,
    ensure_valid_generator,
    ensure_valid_population,
    get_generation_dir,
    get_latest_generation,
    list_demo_generators,
    list_generators,
    load_config,
    merge_constraints,
    normalize_generation_style,
)


def _generations_summary() -> list[dict]:
    """Build summary data for all generations."""
    from .genome import load_population
    from .evolution import calculate_diversity

    latest = get_latest_generation()
    if latest < 0:
        return []

    gens = []
    for gen_num in range(latest + 1):
        gen_dir = get_generation_dir(gen_num)
        pop_file = gen_dir / "population.jsonl"
        winners_file = gen_dir / "winners.json"

        info = {
            "gen_num": gen_num,
            "dir_name": f"gen_{gen_num:03d}",
            "candidates": 0,
            "diversity": 0.0,
            "winners": None,
            "has_contact_sheet": (gen_dir / "contact_sheet.pdf").exists(),
        }

        if pop_file.exists():
            pop = load_population(pop_file)
            info["candidates"] = len(pop)
            info["diversity"] = round(calculate_diversity(pop), 3)

        if winners_file.exists():
            with open(winners_file) as f:
                w = json.load(f)
            info["winners"] = w["winner_indices"]

        gens.append(info)

    return gens


def _generation_detail(gen_num: int) -> dict | None:
    """Get detailed data for a single generation."""
    from .genome import load_population
    from .evolution import calculate_diversity
    from .parameters import denormalize_params, load_specs_from_config

    gen_dir = get_generation_dir(gen_num)
    pop_file = gen_dir / "population.jsonl"

    if not pop_file.exists():
        return None

    specs = load_specs_from_config(DEFAULT_CONFIG)
    pop = load_population(pop_file)
    candidates_dir = gen_dir / "candidates"
    parent_lookup = {}
    if gen_num > 0:
        prev_pop_file = get_generation_dir(gen_num - 1) / "population.jsonl"
        if prev_pop_file.exists():
            parent_lookup = {
                genome.id: genome for genome in load_population(prev_pop_file)
            }

    candidates = []
    for genome in pop:
        idx = genome.index
        svg_file = candidates_dir / f"{idx:04d}.svg"
        meta_file = candidates_dir / f"{idx:04d}_meta.json"
        actual_params = denormalize_params(genome.params, specs)

        candidate = {
            "index": idx,
            "id": genome.id,
            "generator": genome.generator,
            "concept": genome.concept,
            "prompt": genome.prompt,
            "params": genome.params,
            "actual_params": actual_params,
            "seed": genome.seed,
            "parents": list(genome.parents) if genome.parents else None,
            "has_svg": svg_file.exists(),
        }

        if genome.parents:
            parent_genomes = [
                parent_lookup[parent_id]
                for parent_id in genome.parents
                if parent_id in parent_lookup
            ]
            if parent_genomes:
                baseline = {}
                for name in actual_params:
                    values = [
                        denormalize_params(parent.params, specs).get(name)
                        for parent in parent_genomes
                    ]
                    values = [value for value in values if value is not None]
                    if values:
                        baseline[name] = sum(values) / len(values)

                candidate["parent_deltas"] = {
                    name: actual_params[name] - baseline[name]
                    for name in actual_params
                    if name in baseline
                }

        if meta_file.exists():
            with open(meta_file) as f:
                candidate["meta"] = json.load(f)

        candidates.append(candidate)

    winners_file = gen_dir / "winners.json"
    winners = None
    if winners_file.exists():
        with open(winners_file) as f:
            winners = json.load(f)

    generators = sorted({genome.generator for genome in pop})
    prompts = sorted({genome.prompt for genome in pop if genome.prompt})
    concepts = sorted({genome.concept for genome in pop if genome.concept})

    return {
        "gen_num": gen_num,
        "candidates": candidates,
        "diversity": round(calculate_diversity(pop), 3),
        "winners": winners,
        "population_size": len(pop),
        "settings": {
            "concept": concepts[0] if len(concepts) == 1 else None,
            "prompt": prompts[0] if len(prompts) == 1 else None,
            "population": len(pop),
            "generator": generators[0] if len(generators) == 1 else None,
        },
    }


def _save_winners(gen_num: int, winner_indices: list[int]) -> dict:
    """Save winner selection (same logic as CLI select command)."""
    from .genome import load_population

    gen_dir = get_generation_dir(gen_num)
    pop_file = gen_dir / "population.jsonl"

    if not pop_file.exists():
        return {"error": f"No population file for gen_{gen_num:03d}"}

    pop = load_population(pop_file)

    valid = [i for i in winner_indices if 1 <= i <= len(pop)]
    if not valid:
        return {"error": "No valid winner indices"}

    winners_data = {
        "generation": gen_num,
        "population_size": len(pop),
        "winner_indices": valid,
        "winner_ids": [pop[i - 1].id for i in valid],
    }

    winners_file = gen_dir / "winners.json"
    with open(winners_file, "w") as f:
        json.dump(winners_data, f, indent=2)

    return {"ok": True, "winners": winners_data}


def _breed_generation(src_gen: int, population: int | None = None) -> dict:
    """Breed next generation — inherits style and concept from source."""
    from .parameters import load_specs_from_config
    from .genome import FormGenome, load_population, save_population
    from .evolution import generate_population, select_winners
    from .render import render_population
    from .contact_sheet import generate_contact_sheet

    config = load_config()
    specs = load_specs_from_config(DEFAULT_CONFIG)
    evo_config = config.get("evolution", {})

    if population is not None:
        population = ensure_valid_population(population)

    src_dir = get_generation_dir(src_gen)
    winners_file = src_dir / "winners.json"
    pop_file = src_dir / "population.jsonl"

    if not winners_file.exists():
        return {"error": f"No winners for gen_{src_gen:03d}"}
    if not pop_file.exists():
        return {"error": f"No population for gen_{src_gen:03d}"}

    # Inherit style from source gen
    style_file = src_dir / "style.json"
    if style_file.exists():
        with open(style_file) as f:
            style = normalize_generation_style(json.load(f))
    else:
        style = build_generation_style(config)

    with open(winners_file) as f:
        winners_data = json.load(f)

    pop = load_population(pop_file)
    parents = select_winners(pop, winners_data["winner_indices"])

    # Carry concept from parents
    parent_concept = next((p.concept for p in parents if p.concept), None)

    new_gen = src_gen + 1
    new_dir = get_generation_dir(new_gen)
    candidates_dir = new_dir / "candidates"
    candidates_dir.mkdir(parents=True, exist_ok=True)

    pop_size = population or evo_config.get("default_population_size", 6)
    mutation_rate = evo_config.get("mutation_rate", 0.4)
    mutation_strength = evo_config.get("mutation_strength", 0.3)

    new_pop = generate_population(
        size=pop_size,
        gen_num=new_gen,
        parents=parents,
        specs=specs,
        mutation_rate=mutation_rate,
        mutation_strength=mutation_strength,
    )

    # Stamp concept onto offspring
    if parent_concept:
        stamped = []
        for g in new_pop:
            stamped.append(
                FormGenome(
                    id=g.id,
                    generator=g.generator,
                    params=g.params,
                    seed=g.seed,
                    parents=g.parents,
                    prompt=g.prompt,
                    concept=parent_concept,
                    created_at=g.created_at,
                )
            )
        new_pop = stamped

    new_pop_file = new_dir / "population.jsonl"
    save_population(new_pop, new_pop_file)

    # Copy style forward
    new_style_file = new_dir / "style.json"
    with open(new_style_file, "w") as f:
        json.dump(style, f, indent=2)

    render_population(
        new_pop,
        candidates_dir,
        canvas_size=(200, 200),
        format="svg",
        style=style,
        specs=specs,
    )

    contact_sheet = new_dir / "contact_sheet.pdf"
    generate_contact_sheet(
        new_pop,
        contact_sheet,
        cols=3,
        rows=2,
        style=style,
        specs=specs,
    )

    return {"ok": True, "new_generation": new_gen, "population_size": len(new_pop)}


def _list_concepts() -> list[dict]:
    """Return available concepts."""
    from .semantics import CONCEPTS

    return [{"name": c.name, "description": c.description} for c in CONCEPTS.values()]


def _generate_gen0(
    concept_name: str | None,
    population: int = 6,
    prompt: str | None = None,
    generator: str | None = None,
) -> dict:
    """Generate gen0 from browser — mirrors CLI gen0 logic."""
    import random as rnd

    from .parameters import load_specs_from_config
    from .genome import FormGenome, save_population
    from .evolution import generate_population
    from .semantics import (
        get_concept,
        pick_generator_for_concept,
        apply_concept_constraints,
    )
    from .translator import explain_constraints
    from .render import render_population
    from .contact_sheet import generate_contact_sheet

    population = ensure_valid_population(population)
    generator = ensure_valid_generator(generator)

    # Reset first
    _reset_generations()
    GENERATIONS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_config()
    specs = load_specs_from_config(DEFAULT_CONFIG)

    sem_concept = get_concept(concept_name) if concept_name else None
    if concept_name and not sem_concept:
        raise ValueError(f"Unknown concept '{concept_name}'.")

    constraints = apply_concept_constraints(sem_concept) if sem_concept else {}
    constraints = merge_constraints(constraints, prompt)
    base_style = build_generation_style(config, sem_concept)

    gen_num = 0
    gen_dir = get_generation_dir(gen_num)
    candidates_dir = gen_dir / "candidates"
    candidates_dir.mkdir(parents=True, exist_ok=True)

    pop = []
    for i in range(population):
        if sem_concept:
            gen_type = pick_generator_for_concept(sem_concept, rnd.Random(i))
        else:
            gen_types = list_demo_generators()
            gen_type = gen_types[i % len(gen_types)]
        if generator:
            gen_type = generator

        batch = generate_population(
            size=1,
            gen_num=gen_num,
            specs=specs,
            prompt_constraints=constraints or None,
            generator=gen_type,
        )
        g = batch[0]
        pop.append(
            FormGenome(
                id=f"gen{gen_num:03d}_{i + 1:04d}",
                generator=gen_type,
                params=g.params,
                seed=g.seed,
                parents=g.parents,
                prompt=prompt,
                concept=sem_concept.name if sem_concept else None,
                created_at=g.created_at,
            )
        )

    pop_file = gen_dir / "population.jsonl"
    save_population(pop, pop_file)

    style_file = gen_dir / "style.json"
    with open(style_file, "w") as f:
        json.dump(base_style, f, indent=2)

    render_population(
        pop,
        candidates_dir,
        canvas_size=(200, 200),
        format="svg",
        style=base_style,
        specs=specs,
    )

    contact_sheet = gen_dir / "contact_sheet.pdf"
    generate_contact_sheet(
        pop, contact_sheet, cols=3, rows=2, style=base_style, specs=specs
    )

    return {
        "ok": True,
        "concept": concept_name,
        "population_size": len(pop),
        "prompt": prompt,
        "generator": generator,
        "constraints": explain_constraints(constraints) if constraints else None,
    }


def _reset_generations() -> dict:
    """Trash all generations and return clean state."""
    if not GENERATIONS_DIR.exists():
        return {"ok": True}
    trash_bin = shutil.which("trash")
    for d in sorted(GENERATIONS_DIR.iterdir()):
        if d.is_dir() and d.name.startswith("gen_"):
            if trash_bin:
                import subprocess

                subprocess.run([trash_bin, str(d)], check=False)
            else:
                shutil.rmtree(d, ignore_errors=True)
    return {"ok": True}


class EvolveHandler(BaseHTTPRequestHandler):
    """HTTP handler for the evolve browser."""

    def log_message(self, format, *args):
        """Suppress default logging noise."""
        pass

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str):
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path):
        if not path.exists() or not path.is_file():
            self.send_error(404)
            return
        # Security: ensure path is under GENERATIONS_DIR
        try:
            path.resolve().relative_to(GENERATIONS_DIR.resolve())
        except ValueError:
            self.send_error(403)
            return

        mime, _ = mimetypes.guess_type(str(path))
        mime = mime or "application/octet-stream"

        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "max-age=3600")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/" or path == "":
            self._send_html(GALLERY_HTML)
            return

        if path == "/api/concepts":
            config = load_config()
            self._send_json(
                {
                    "concepts": _list_concepts(),
                    "generators": list_generators(),
                    "default_population": config.get("evolution", {}).get(
                        "default_population_size", 6
                    ),
                }
            )
            return

        if path == "/api/generations":
            self._send_json({"generations": _generations_summary()})
            return

        if path.startswith("/api/generation/"):
            try:
                gen_num = int(path.split("/")[3])
            except (IndexError, ValueError):
                self.send_error(400)
                return
            detail = _generation_detail(gen_num)
            if detail is None:
                self.send_error(404)
                return
            self._send_json(detail)
            return

        # Serve SVG/files: /files/gen_000/candidates/0001.svg
        if path.startswith("/files/"):
            rel = path[len("/files/") :]
            file_path = GENERATIONS_DIR / rel
            self._send_file(file_path)
            return

        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b""

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self.send_error(400)
            return

        if path == "/api/select":
            gen_num = data.get("generation")
            winners = data.get("winners", [])
            if gen_num is None or not winners:
                self._send_json({"error": "Need generation and winners"}, 400)
                return
            result = _save_winners(int(gen_num), [int(w) for w in winners])
            status = 200 if "ok" in result else 400
            self._send_json(result, status)
            return

        if path == "/api/generate":
            try:
                concept = data.get("concept")
                prompt = data.get("prompt")
                generator = data.get("generator")
                pop_size = int(data.get("population", 6))
                result = _generate_gen0(
                    concept, pop_size, prompt=prompt, generator=generator
                )
                status = 200 if "ok" in result else 400
                self._send_json(result, status)
            except Exception as exc:
                self._send_json({"error": str(exc)}, 400)
            return

        if path == "/api/reset":
            result = _reset_generations()
            status = 200 if "ok" in result else 400
            self._send_json(result, status)
            return

        if path == "/api/breed":
            src_gen = data.get("generation")
            pop_size = data.get("population")
            if src_gen is None:
                self._send_json({"error": "Need generation"}, 400)
                return
            try:
                population = int(pop_size) if pop_size is not None else None
                result = _breed_generation(int(src_gen), population)
                status = 200 if "ok" in result else 400
                self._send_json(result, status)
            except Exception as exc:
                self._send_json({"error": str(exc)}, 400)
            return

        self.send_error(404)


GALLERY_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Evolve Browser</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: "SF Mono", "Menlo", "Consolas", monospace;
    background: #fff; color: #111;
    min-height: 100vh;
  }
  header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 16px 24px; border-bottom: 1px solid #ddd;
    position: sticky; top: 0; background: #fff; z-index: 100;
  }
  header h1 { font-size: 14px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; color: #000; }
  .gen-nav {
    display: flex; align-items: center; gap: 8px;
  }
  .gen-nav button, .gen-nav select {
    background: #fff; color: #111; border: 1px solid #ccc;
    padding: 6px 12px; font-family: inherit; font-size: 12px;
    cursor: pointer; border-radius: 3px;
  }
  .gen-nav button:hover { background: #f0f0f0; }
  .gen-nav button:disabled { opacity: 0.3; cursor: default; }
  .gen-nav select { appearance: none; padding-right: 24px;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%23666'/%3E%3C/svg%3E");
    background-repeat: no-repeat; background-position: right 8px center;
  }

  .stats {
    display: flex; gap: 24px; padding: 12px 24px;
    border-bottom: 1px solid #eee; font-size: 11px; color: #666;
  }
  .stats span { }
  .stats .label { color: #999; }
  .stats .value { color: #333; margin-left: 4px; }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    grid-auto-rows: minmax(220px, 1fr);
    gap: 8px;
    padding: 8px 8px 88px;
    height: calc(100vh - 49px - 36px);
    overflow-y: auto;
    align-content: start;
  }

  .cell {
    position: relative; background: #fff;
    cursor: pointer; overflow: hidden;
    transition: outline 0.1s;
    outline: 2px solid transparent; outline-offset: -2px;
    aspect-ratio: 1;
  }
  .cell:hover { background: #f8f8f8; }
  .cell.selected { outline-color: #000; }
  .cell.winner { outline-color: #999; }

  .cell svg, .cell img {
    width: 100%; height: 100%;
    display: block; object-fit: contain;
  }
  .cell .label {
    position: absolute; bottom: 4px; right: 6px;
    font-size: 10px; color: #ccc;
    pointer-events: none;
  }
  .cell .index-badge {
    position: absolute; top: 4px; left: 6px;
    font-size: 18px; font-weight: 700; color: #ddd;
    pointer-events: none;
  }
  .cell.selected .index-badge { color: #000; }
  .cell.winner .index-badge { color: #999; }

  .cell .parent-tag {
    position: absolute; top: 4px; right: 6px;
    font-size: 9px; color: #ccc; pointer-events: none;
  }

  .actions {
    position: fixed; bottom: 0; left: 0; right: 0;
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 24px; background: #fff; border-top: 1px solid #ddd;
    z-index: 100;
  }
  .actions .sel-count { font-size: 12px; color: #999; }
  .actions .btn-group { display: flex; gap: 8px; }

  .btn {
    padding: 8px 20px; font-family: inherit; font-size: 12px;
    border: 1px solid #ccc; background: #fff; color: #111;
    cursor: pointer; border-radius: 3px; font-weight: 500;
    text-transform: uppercase; letter-spacing: 0.05em;
  }
  .btn:hover { background: #f0f0f0; }
  .btn:disabled { opacity: 0.3; cursor: default; }
  .btn.primary { background: #000; color: #fff; border-color: #000; }
  .btn.primary:hover { background: #333; }
  .btn.primary:disabled { background: #ccc; border-color: #ccc; color: #999; }
  .btn.breed { background: #000; color: #fff; border-color: #000; }
  .btn.breed:hover { background: #333; }
  .btn.reset { border-color: #ccc; color: #999; }
  .btn.reset:hover { background: #f5f0f0; color: #c00; border-color: #c00; }

  .toast {
    position: fixed; top: 20px; right: 20px;
    padding: 10px 16px; background: #fff; border: 1px solid #ccc;
    font-size: 12px; border-radius: 3px; z-index: 200;
    opacity: 0; transition: opacity 0.3s; color: #111;
  }
  .toast.show { opacity: 1; }
  .toast.ok { border-color: #000; }
  .toast.err { border-color: #c00; }

  .detail-panel {
    position: fixed; top: 0; right: -400px; bottom: 0; width: 380px;
    background: #fff; border-left: 1px solid #ddd;
    transition: right 0.2s; z-index: 150; overflow-y: auto;
    padding: 20px;
  }
  .detail-panel.open { right: 0; }
  .detail-panel h2 { font-size: 13px; margin-bottom: 12px; }
  .detail-panel .close {
    position: absolute; top: 12px; right: 12px;
    background: none; border: none; color: #999; cursor: pointer;
    font-size: 18px; font-family: inherit;
  }
  .detail-panel .preview { width: 100%; aspect-ratio: 1; background: #fff; margin-bottom: 16px; border: 1px solid #eee; }
  .detail-panel .preview svg, .detail-panel .preview img { width: 100%; height: 100%; }
  .detail-panel dl { font-size: 11px; }
  .detail-panel dt { color: #999; margin-top: 8px; }
  .detail-panel dd { color: #333; margin-left: 0; }
  .detail-panel .muted { color: #999; }
  .detail-panel .section-title {
    margin: 18px 0 8px;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #999;
  }

  .spinner {
    display: inline-block; width: 14px; height: 14px;
    border: 2px solid #ccc; border-top-color: #000;
    border-radius: 50%; animation: spin 0.6s linear infinite;
    vertical-align: middle; margin-right: 6px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .empty {
    display: flex; align-items: center; justify-content: center;
    min-height: 60vh; color: #999; font-size: 13px;
  }

  .concept-picker {
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; min-height: calc(100vh - 49px - 36px);
    padding: 40px;
  }
  .picker-title {
    font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em;
    color: #999; margin-bottom: 24px;
  }
  .picker-subtitle {
    font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em;
    color: #999; margin: 24px 0 12px;
  }
  .picker-controls {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    width: min(760px, 100%);
  }
  .picker-field {
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: 11px;
    color: #666;
  }
  .picker-field.prompt {
    grid-column: span 3;
  }
  .picker-field input,
  .picker-field select {
    width: 100%;
    padding: 10px 12px;
    border: 1px solid #ddd;
    border-radius: 3px;
    background: #fff;
    color: #111;
    font: inherit;
  }
  .concepts {
    display: grid; grid-template-columns: repeat(5, 1fr);
    gap: 8px; max-width: 700px; width: 100%;
  }
  .concept-btn {
    padding: 16px 12px; background: #fff; border: 1px solid #ddd;
    cursor: pointer; text-align: center; font-family: inherit;
    border-radius: 3px; transition: all 0.15s;
  }
  .concept-btn:hover { border-color: #000; }
  .concept-btn .name {
    font-size: 12px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.05em; display: block; margin-bottom: 4px;
  }
  .concept-btn .desc {
    font-size: 10px; color: #999; display: block;
  }

  @media (max-width: 900px) {
    .picker-controls,
    .concepts {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .picker-field.prompt {
      grid-column: span 2;
    }
    .grid {
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      grid-auto-rows: minmax(160px, 1fr);
    }
  }
</style>
</head>
<body>

<header>
  <h1>Evolve</h1>
  <div class="gen-nav">
    <button id="prev-gen" onclick="navGen(-1)">&larr;</button>
    <select id="gen-select" onchange="loadGen(+this.value)"></select>
    <button id="next-gen" onclick="navGen(1)">&rarr;</button>
  </div>
</header>

<div class="stats" id="stats"></div>
<div class="concept-picker" id="concept-picker" style="display:none">
  <div class="picker-title" id="picker-title">Start a generation</div>
  <div class="picker-controls">
    <label class="picker-field">
      <span>Population</span>
      <input id="population-input" type="number" min="1" max="64" value="6">
    </label>
    <label class="picker-field">
      <span>Generator</span>
      <select id="generator-select"></select>
    </label>
    <label class="picker-field prompt">
      <span>Prompt</span>
      <input id="prompt-input" type="text" placeholder="soft protective rounded, dense, tall...">
    </label>
  </div>
  <div class="picker-subtitle">Choose a concept</div>
  <div class="concepts" id="concepts"></div>
</div>
<div class="grid" id="grid"></div>

<div class="actions" id="actions" style="display:none">
  <div class="sel-count" id="sel-count">0 selected</div>
  <div class="btn-group">
    <button class="btn" onclick="clearSelection()">Clear</button>
    <button class="btn" id="regen-btn" onclick="regenerateGeneration()" disabled>Restart From Settings</button>
    <button class="btn reset" onclick="resetAll()">Reset</button>
    <button class="btn primary" id="save-btn" onclick="saveWinners()" disabled>Save Winners</button>
    <button class="btn breed" id="breed-btn" onclick="breedNext()" disabled title="Select and save winners first">Breed Next Gen</button>
  </div>
</div>

<div class="detail-panel" id="detail">
  <button class="close" onclick="closeDetail()">&times;</button>
  <div id="detail-content"></div>
</div>

<div class="toast" id="toast"></div>

<script>
let generations = [];
let currentGen = null;
let genData = null;
let selected = new Set();
let existingWinners = new Set();
let pickerOptions = null;
let lastGenerateRequest = null;

async function init() {
  const r = await fetch('/api/generations');
  const d = await r.json();
  generations = d.generations;
  if (!generations.length) {
    showConceptPicker();
    return;
  }
  document.getElementById('concept-picker').style.display = 'none';
  document.getElementById('grid').style.display = '';
  populateSelect();
  loadGen(generations[generations.length - 1].gen_num);
}

async function loadPickerOptions() {
  if (pickerOptions) return pickerOptions;
  const r = await fetch('/api/concepts');
  pickerOptions = await r.json();
  return pickerOptions;
}

function populatePickerControls(prefill = {}) {
  const defaults = pickerOptions || { generators: [], default_population: 6 };
  const generatorSelect = document.getElementById('generator-select');
  generatorSelect.innerHTML = [
    '<option value="">Auto-select</option>',
    ...defaults.generators.map(name => `<option value="${name}">${name}</option>`),
  ].join('');

  document.getElementById('population-input').value = prefill.population || defaults.default_population || 6;
  document.getElementById('prompt-input').value = prefill.prompt || '';
  generatorSelect.value = prefill.generator || '';
  document.getElementById('picker-title').textContent = prefill.title || 'Start a generation';
}

function readPickerConfig(concept) {
  const population = Number.parseInt(document.getElementById('population-input').value || '0', 10);
  const prompt = document.getElementById('prompt-input').value.trim();
  const generator = document.getElementById('generator-select').value || null;
  return {
    concept,
    population,
    prompt: prompt || null,
    generator,
  };
}

async function showConceptPicker(prefill = null) {
  document.getElementById('grid').style.display = 'none';
  document.getElementById('actions').style.display = 'none';
  document.getElementById('stats').innerHTML = '';
  const picker = document.getElementById('concept-picker');
  picker.style.display = '';

  const options = await loadPickerOptions();
  populatePickerControls(prefill || {});
  const container = document.getElementById('concepts');
  container.innerHTML = options.concepts.map(c =>
    `<button class="concept-btn" onclick="generateWithConcept('${c.name}')">
      <span class="name">${c.name}</span>
      <span class="desc">${c.description}</span>
    </button>`
  ).join('') +
    `<button class="concept-btn" onclick="generateWithConcept(null)">
      <span class="name">None</span>
      <span class="desc">No concept, all generators</span>
    </button>`;
}

async function requestGeneration(config) {
  const pickerTitle = document.getElementById('picker-title');
  pickerTitle.innerHTML = '<span class="spinner"></span> Generating...';

  const r = await fetch('/api/generate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(config),
  });
  const d = await r.json();
  if (d.ok) {
    lastGenerateRequest = config;
    toast('Generation 0 created', 'ok');
    document.getElementById('concept-picker').style.display = 'none';
    document.getElementById('grid').style.display = '';
    await init();
    return;
  }

  toast(d.error || 'Generation failed', 'err');
  await showConceptPicker({ ...config, title: 'Start a generation' });
}

async function generateWithConcept(concept) {
  await requestGeneration(readPickerConfig(concept));
}

async function regenerateGeneration() {
  const settings = genData?.settings || lastGenerateRequest;
  if (!settings) return;
  if (!confirm('Replace existing generations and restart from these settings?')) return;

  await requestGeneration({
    concept: settings.concept || null,
    population: settings.population || pickerOptions?.default_population || 6,
    prompt: settings.prompt || null,
    generator: settings.generator || null,
  });
}

function populateSelect() {
  const sel = document.getElementById('gen-select');
  sel.innerHTML = generations.map(g =>
    `<option value="${g.gen_num}">gen_${String(g.gen_num).padStart(3,'0')} (${g.candidates})</option>`
  ).join('');
}

function navGen(delta) {
  const idx = generations.findIndex(g => g.gen_num === currentGen);
  const next = idx + delta;
  if (next >= 0 && next < generations.length) {
    loadGen(generations[next].gen_num);
  }
}

async function loadGen(num) {
  currentGen = num;
  selected.clear();
  existingWinners.clear();

  document.getElementById('gen-select').value = num;
  updateNavButtons();

  const r = await fetch(`/api/generation/${num}`);
  genData = await r.json();
  lastGenerateRequest = genData.settings || lastGenerateRequest;

  if (genData.winners) {
    genData.winners.winner_indices.forEach(i => existingWinners.add(i));
    // Pre-select existing winners
    existingWinners.forEach(i => selected.add(i));
  }

  renderStats();
  renderGrid();
  updateActions();
}

function renderStats() {
  const s = document.getElementById('stats');
  const concept = genData.settings?.concept;
  const generator = genData.settings?.generator;
  const prompt = genData.settings?.prompt;
  s.innerHTML = `
    ${concept ? `<span><span class="label">Concept</span><span class="value" style="text-transform:uppercase;letter-spacing:0.1em">${concept}</span></span>` : ''}
    ${generator ? `<span><span class="label">Generator</span><span class="value">${generator}</span></span>` : ''}
    <span><span class="label">Candidates</span><span class="value">${genData.population_size}</span></span>
    <span><span class="label">Diversity</span><span class="value">${genData.diversity}</span></span>
    <span><span class="label">Winners</span><span class="value">${genData.winners ? genData.winners.winner_indices.join(', ') : 'none'}</span></span>
    ${prompt ? `<span><span class="label">Prompt</span><span class="value">${prompt}</span></span>` : ''}
  `;
}

function renderGrid() {
  const grid = document.getElementById('grid');
  grid.innerHTML = genData.candidates.map(c => {
    const isSelected = selected.has(c.index);
    const isWinner = existingWinners.has(c.index);
    const cls = ['cell'];
    if (isSelected) cls.push('selected');
    if (isWinner && !isSelected) cls.push('winner');

    const parents = c.parents ? `<div class="parent-tag">${c.parents.map(p => p.split('_')[1]).join('+')}</div>` : '';

    return `<div class="${cls.join(' ')}" data-idx="${c.index}"
                 onclick="toggleSelect(${c.index}, event)"
                 ondblclick="showDetail(${c.index})">
      ${c.has_svg ? `<img src="/files/gen_${String(currentGen).padStart(3,'0')}/candidates/${String(c.index).padStart(4,'0')}.svg" loading="lazy">` : ''}
      <div class="index-badge">${c.index}</div>
      ${parents}
      <div class="label">${c.generator}</div>
    </div>`;
  }).join('');
}

function syncGridSelectionState() {
  document.querySelectorAll('#grid .cell').forEach(cell => {
    const idx = Number.parseInt(cell.dataset.idx, 10);
    cell.classList.toggle('selected', selected.has(idx));
    cell.classList.toggle('winner', existingWinners.has(idx) && !selected.has(idx));
  });
}

function toggleSelect(idx, event) {
  if (event && event.detail === 2) return; // skip on dblclick
  if (selected.has(idx)) {
    selected.delete(idx);
  } else {
    selected.add(idx);
  }
  syncGridSelectionState();
  updateActions();
}

function clearSelection() {
  selected.clear();
  syncGridSelectionState();
  updateActions();
}

function updateActions() {
  const bar = document.getElementById('actions');
  bar.style.display = genData ? 'flex' : 'none';

  const hasWinners = genData && genData.winners;
  const count = document.getElementById('sel-count');

  if (hasWinners) {
    count.textContent = `${selected.size} selected`;
  } else if (selected.size > 0) {
    count.textContent = `${selected.size} selected — save winners to enable breeding`;
  } else {
    count.textContent = 'Click candidates to select winners';
  }

  document.getElementById('save-btn').disabled = selected.size === 0;
  document.getElementById('breed-btn').disabled = !hasWinners;
  const regenBtn = document.getElementById('regen-btn');
  regenBtn.disabled = !genData?.settings;
  regenBtn.textContent = currentGen === 0 ? 'Regenerate Gen0' : 'Restart From Settings';
}

function updateNavButtons() {
  const idx = generations.findIndex(g => g.gen_num === currentGen);
  document.getElementById('prev-gen').disabled = idx <= 0;
  document.getElementById('next-gen').disabled = idx >= generations.length - 1;
}

async function saveWinners() {
  const btn = document.getElementById('save-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Saving...';

  const r = await fetch('/api/select', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      generation: currentGen,
      winners: Array.from(selected).sort((a,b) => a-b),
    }),
  });
  const d = await r.json();

  if (d.ok) {
    toast('Winners saved', 'ok');
    await loadGen(currentGen);
    // Refresh generation list
    const gr = await fetch('/api/generations');
    const gd = await gr.json();
    generations = gd.generations;
    populateSelect();
    document.getElementById('gen-select').value = currentGen;
  } else {
    toast(d.error || 'Failed', 'err');
  }

  btn.innerHTML = 'Save Winners';
  btn.disabled = selected.size === 0;
}

async function breedNext() {
  const btn = document.getElementById('breed-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Breeding...';

  const r = await fetch('/api/breed', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ generation: currentGen }),
  });
  const d = await r.json();

  if (d.ok) {
    toast(`Generation ${d.new_generation} created (${d.population_size} candidates)`, 'ok');
    // Refresh
    const gr = await fetch('/api/generations');
    const gd = await gr.json();
    generations = gd.generations;
    populateSelect();
    loadGen(d.new_generation);
  } else {
    toast(d.error || 'Breed failed', 'err');
  }

  btn.innerHTML = 'Breed Next Gen';
  updateActions();
}

async function resetAll() {
  if (!confirm('Trash all generations and start fresh?')) return;
  const r = await fetch('/api/reset', { method: 'POST' });
  const d = await r.json();
  if (d.ok) {
    toast('All generations trashed', 'ok');
    generations = [];
    genData = null;
    selected.clear();
    existingWinners.clear();
    document.getElementById('gen-select').innerHTML = '';
    showConceptPicker();
  } else {
    toast('Reset failed', 'err');
  }
}

function showDetail(idx) {
  const c = genData.candidates.find(x => x.index === idx);
  if (!c) return;

  const panel = document.getElementById('detail');
  const content = document.getElementById('detail-content');

  const svgUrl = `/files/gen_${String(currentGen).padStart(3,'0')}/candidates/${String(idx).padStart(4,'0')}.svg`;

  let paramsHtml = Object.entries(c.actual_params || {})
    .map(([k, actual]) => `<dt>${k}</dt><dd>${formatParamValue(actual)} <span class="muted">(${c.params[k].toFixed(3)} norm)</span></dd>`)
    .join('');
  const deltas = Object.entries(c.parent_deltas || {})
    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
    .slice(0, 6);
  const deltaHtml = deltas.length
    ? `<div class="section-title">Vs Parents</div><dl>${
        deltas.map(([k, v]) => `<dt>${k}</dt><dd>${formatDelta(v)}</dd>`).join('')
      }</dl>`
    : '';

  content.innerHTML = `
    <h2>${c.id}</h2>
    <div class="preview"><img src="${svgUrl}"></div>
    <dl>
      ${c.concept ? `<dt>Concept</dt><dd>${c.concept}</dd>` : ''}
      ${c.prompt ? `<dt>Prompt</dt><dd>${c.prompt}</dd>` : ''}
      <dt>Generator</dt><dd>${c.generator}</dd>
      <dt>Seed</dt><dd>${c.seed}</dd>
      ${c.parents ? `<dt>Parents</dt><dd>${c.parents.join(' + ')}</dd>` : ''}
    </dl>
    <div class="section-title">Parameters</div>
    <dl>${paramsHtml}</dl>
    ${deltaHtml}
  `;

  panel.classList.add('open');
}

function closeDetail() {
  document.getElementById('detail').classList.remove('open');
}

function formatParamValue(value) {
  if (typeof value !== 'number') return String(value);
  if (Number.isInteger(value)) return String(value);
  if (Math.abs(value) >= 10) return value.toFixed(1);
  if (Math.abs(value) >= 1) return value.toFixed(2);
  return value.toFixed(3);
}

function formatDelta(value) {
  const sign = value > 0 ? '+' : '';
  return `${sign}${formatParamValue(value)}`;
}

function toast(msg, type) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show ' + (type || '');
  setTimeout(() => t.classList.remove('show'), 2500);
}

// Keyboard shortcuts
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeDetail();
  if (e.key === 'ArrowLeft') navGen(-1);
  if (e.key === 'ArrowRight') navGen(1);
});

init();
</script>
</body>
</html>
"""


def run_server(host: str = "127.0.0.1", port: int = 8000, open_browser: bool = True):
    """Start the evolve browser server."""

    class ThreadedServer(ThreadingMixIn, HTTPServer):
        daemon_threads = True

    server = ThreadedServer((host, port), EvolveHandler)
    url = f"http://{host}:{port}"

    if open_browser:
        webbrowser.open(url)

    print(f"Evolve browser: {url}")
    print("Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()
