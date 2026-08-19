"""Source renderer for Musiculum's default long-session V3 interface."""

from __future__ import annotations

import html
import json
import math
import re
from pathlib import Path


ASSETS_DIR = Path(__file__).resolve().parent / "assets"


def parse_front_matter(markdown_text: str) -> tuple[dict[str, object], str]:
    lines = markdown_text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, markdown_text
    try:
        closing = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        return {}, markdown_text

    metadata: dict[str, object] = {}
    current_map: dict[str, str] | None = None
    for line in lines[1:closing]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0].isspace():
            if current_map is not None and ":" in line:
                key, value = line.strip().split(":", 1)
                current_map[key.strip().strip('"')] = value.strip().strip('"')
            continue
        key, separator, value = line.partition(":")
        if not separator:
            continue
        if value.strip():
            metadata[key.strip()] = value.strip().strip('"')
            current_map = None
        else:
            current_map = {}
            metadata[key.strip()] = current_map
    return metadata, "\n".join(lines[closing + 1 :])


def inline_markdown(value: str) -> str:
    rendered = html.escape(value)
    rendered = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", rendered)
    rendered = re.sub(r"\*(.+?)\*", r"<em>\1</em>", rendered)
    return re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2" target="_blank" rel="noopener">\1</a>',
        rendered,
    )


def extract_sections(markdown_text: str) -> list[dict[str, object]]:
    sections: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    in_code = False
    for raw_line in markdown_text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code or stripped.startswith("# ") or stripped.startswith("|"):
            continue
        if stripped.startswith("## "):
            current = {"heading": stripped[3:].replace("*", "").strip(), "paragraphs": []}
            sections.append(current)
            continue
        if stripped and current is not None and not re.match(r"^-{3,}$", stripped):
            paragraphs = current["paragraphs"]
            assert isinstance(paragraphs, list)
            paragraphs.append(inline_markdown(stripped))
    return sections


def album_key(row: dict) -> str:
    return f"{row.get('artist', '')} - {row.get('album', '')}"


def era_key(heading: str) -> str:
    return heading.split(":", 1)[0].strip()


def era_setting(metadata: dict[str, object], setting: str, heading: str, default: str = "") -> str:
    values = metadata.get(setting)
    if not isinstance(values, dict):
        return default
    return str(values.get(era_key(heading), default))


def year_range(albums: list[dict]) -> str:
    years = [int(str(row["year"])) for row in albums if str(row.get("year", "")).isdigit()]
    if not years:
        return ""
    return str(min(years)) if min(years) == max(years) else f"{min(years)}–{max(years)}"


def album_card(row: dict) -> str:
    key = album_key(row)
    key_attr = html.escape(key, quote=True)
    artist = html.escape(str(row.get("artist", "")))
    album = html.escape(str(row.get("album", "")))
    year = html.escape(str(row.get("year", "")))
    note = html.escape(str(row.get("note", "")))
    cue = html.escape(str(row.get("listen_for", "Follow the central texture against the rhythm section.")))
    energy = html.escape(str(row.get("energy", "5")))
    texture = html.escape(str(row.get("texture", "unclassified")))
    return f"""<article class="album-card" data-key="{key_attr}" data-card-key="{key_attr}">
      <div class="card-meta"><span>{artist}</span><span>{year}</span></div>
      <h3>{album}</h3><p class="note">{note}</p>
      <p class="cue"><strong>Listen for</strong>{cue}</p>
      <div class="tags"><span class="tag">Energy {energy}/10</span><span class="tag">{texture}</span></div>
      <div class="card-actions"><button class="load-player" data-key="{key_attr}">Load player</button>
      <button class="bookmark" data-key="{key_attr}" aria-label="Bookmark {artist} - {album}" aria-pressed="false">☆</button></div>
    </article>"""


TEXTURE_SIGNALS: dict[str, tuple[str, ...]] = {
    "abrasive": (
        "noise", "distort", "harsh", "feedback", "scream", "aggress", "brutal", "fuzz", "grind", "snarl",
        "riff", "abras", "detuned", "dissonan", "metal", "clang", "sludge", "caustic", "shred",
    ),
    "atmospheric": (
        "reverb", "ambient", "haze", "dream", "gauze", "gauzy", "ethereal", "shimmer", "blur", "cloud",
        "wash", "narcotic", "gossamer", "drone", "laptop", "glitch", "process", "synth", "abstract",
        "granular", "electronic", "shoegaze", "smear", "veil", "submerg",
    ),
    "cavernous": (
        "vast", "cathedral", "echo", "sprawl", "epic", "monument", "immense", "expansive", "crescendo",
        "cavern", "architect", "instrumental", "orchestral", "symphon", "swell", "expanse", "immersi",
        "post-rock", "post rock",
    ),
    "crystalline": (
        "clean", "bright", "precise", "delicate", "chime", "pristine", "clarity", "glassy", "melod",
        "gleam", "composition", "classical", "chamber", "arrange", "piano", "string", "formal",
        "intricate", "filigree",
    ),
    "propulsive": (
        "rhythm", "drive", "motorik", "groove", "pulse", "momentum", "kinetic", "percussi", "drum",
        "funk", "velocity", "propuls", "math", "angular", "geometr", "polyrhythm", "syncopat",
        "krautrock", "jazz", "insistent",
    ),
    "spare": (
        "minimal", "quiet", "sparse", "silence", "restraint", "hushed", "austere", "acoustic", "fragile",
        "still", "empty", "spare", "tape", "lo-fi", "bedroom", "field record", "unadorned", "reduc",
        "understat", "stark",
    ),
}

ENERGY_SIGNALS: tuple[tuple[int, tuple[str, ...]], ...] = (
    (2, ("brutal", "explos", "punish", "ferocious", "relentless", "violent", "blast", "crush", "obliterat")),
    (
        1,
        (
            "aggress", "loud", "heavy", "distort", "frantic", "rush", "euphoric", "anthem", "roar",
            "intens", "scream", "noise", "propuls", "urgent", "surge", "maximal", "dense", "climax",
            "crescendo", "attack", "kinetic",
        ),
    ),
    (
        -1,
        (
            "gentle", "delicate", "sparse", "subtle", "tender", "drift", "slow", "soft", "patient",
            "restraint", "sustain", "understat", "unhurried", "spacious", "reflective", "meditative",
        ),
    ),
    (-2, ("quiet", "minimal", "hushed", "silence", "ambient", "still", "austere", "fragile", "glacial", "stasis")),
)


TEXTURE_BASE_ENERGY: dict[str, int] = {
    "abrasive": 8,
    "propulsive": 7,
    "cavernous": 6,
    "atmospheric": 5,
    "crystalline": 4,
    "spare": 3,
}


def infer_texture(text: str) -> str:
    scores = {
        texture: sum(1 for signal in signals if signal in text)
        for texture, signals in TEXTURE_SIGNALS.items()
    }
    best = max(scores.values())
    if not best:
        return "unclassified"
    return min(texture for texture, score in scores.items() if score == best)


def infer_energy(text: str, texture: str) -> int:
    score = TEXTURE_BASE_ENERGY.get(texture, 5)
    for weight, signals in ENERGY_SIGNALS:
        hits = sum(1 for signal in signals if signal in text)
        score += weight * min(hits, 2)
    return max(1, min(10, score))


def infer_missing_fields(records: list[dict]) -> int:
    """Fill absent V3 columns from the essay prose so every guide gets a usable map."""
    touched = 0
    for row in records:
        text = f"{row.get('note', '')} {row.get('listen_for', '')} {row.get('section', '')}".casefold()
        if not row.get("texture"):
            row["texture"] = infer_texture(text)
            touched += 1
        if not row.get("energy"):
            row["energy"] = str(infer_energy(text, str(row["texture"])))
            touched += 1
        if not row.get("listen_for"):
            row["listen_for"] = f"How the {row['texture']} surface sits against the rhythm section."

    by_section: dict[str, list[dict]] = {}
    for row in records:
        by_section.setdefault(str(row.get("section", "General")), []).append(row)

    for row in records:
        if row.get("connections"):
            continue
        peers = by_section[str(row.get("section", "General"))]
        position = peers.index(row)
        links = [peers[(position + 1) % len(peers)]["key"]] if len(peers) > 1 else []
        cross = next(
            (
                other["key"]
                for other in records
                if other["texture"] == row["texture"]
                and other.get("section") != row.get("section")
                and other["key"] not in links
            ),
            "",
        )
        if cross:
            links.append(cross)
        row["connections"] = "; ".join(dict.fromkeys(link for link in links if link != row["key"]))
    return touched


def render_v3(title: str, markdown_text: str, catalog: list[dict], found_count: int) -> str:
    metadata, essay = parse_front_matter(markdown_text)
    sections = extract_sections(essay)
    hero_paragraphs: list[str] = []
    if sections and str(sections[0]["heading"]).casefold() == "executive summary":
        first = sections.pop(0)
        hero_paragraphs = list(first["paragraphs"])

    records = [{**row, "key": album_key(row)} for row in catalog]
    record_keys = {row["key"] for row in records}
    inferred = infer_missing_fields(records)
    for row in records:
        connections = [item.strip() for item in str(row.get("connections", "")).split(";") if item.strip()]
        missing = [item for item in connections if item not in record_keys]
        if missing:
            raise ValueError(f"Unresolved connections for {row['key']}: {', '.join(missing)}")
        row["connection_keys"] = connections

    routes: dict[str, list[str]] = {}
    configured_routes = metadata.get("routes")
    if isinstance(configured_routes, dict):
        for name, route in configured_routes.items():
            keys = [item.strip() for item in str(route).split(">") if item.strip()]
            missing = [item for item in keys if item not in record_keys]
            if missing:
                raise ValueError(f"Route '{name}' contains unresolved albums: {', '.join(missing)}")
            routes[str(name)] = keys
    if not routes and records:
        routes["start-here"] = [row["key"] for row in records[: min(4, len(records))]]

    by_section: dict[str, list[dict]] = {}
    for row in records:
        by_section.setdefault(str(row.get("section", "General")), []).append(row)

    textures = sorted({str(row.get("texture", "unclassified")) for row in records})
    for row in records:
        energy = int(str(row.get("energy", "5")))
        if not 1 <= energy <= 10:
            raise ValueError(f"Energy must be 1–10: {row['key']}")

    # Row height follows the densest energy column so crowded guides stay legible.
    bucket_sizes: dict[tuple[str, int], int] = {}
    for row in records:
        bucket = (str(row.get("texture", "unclassified")), int(str(row.get("energy", "5"))))
        bucket_sizes[bucket] = bucket_sizes.get(bucket, 0) + 1
    row_heights = {
        texture: max(62, 30 + max((size for (tex, _), size in bucket_sizes.items() if tex == texture), default=1) * 15)
        for texture in textures
    }
    row_tops: dict[str, float] = {}
    cursor = 50.0
    for texture in textures:
        row_tops[texture] = cursor
        cursor += row_heights[texture]

    map_width, map_height = 920, int(max(330, cursor + 40))
    buckets: dict[tuple[int, str], int] = {}
    map_points: list[str] = []
    for row in records:
        energy = int(str(row.get("energy", "5")))
        texture = str(row.get("texture", "unclassified"))
        bucket = (energy, texture)
        offset = buckets.get(bucket, 0)
        buckets[bucket] = offset + 1
        x = 70 + ((energy - 1) / 9) * (map_width - 120) + (offset % 2) * 9
        y = row_tops[texture] + 20 + offset * 15
        key_attr = html.escape(row["key"], quote=True)
        label = (
            f'<text x="{x + 14:.1f}" y="{y + 4:.1f}">{html.escape(str(row["artist"]))}</text>'
            if bucket_sizes[(texture, energy)] <= 6
            else ""
        )
        map_points.append(
            f'<g class="map-point record-target" data-key="{key_attr}" tabindex="0" role="button" '
            f'aria-label="{key_attr}, energy {energy}, {html.escape(texture, quote=True)}">'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="9"></circle>{label}</g>'
        )
    map_labels = "".join(
        f'<text class="axis-label" x="12" y="{row_tops[texture] + 18:.1f}">{html.escape(texture)}</text>'
        for texture in textures
    )

    graph_width, graph_height = 920, 560
    positions: dict[str, tuple[float, float]] = {}
    for index, row in enumerate(records):
        angle = (2 * math.pi * index / max(1, len(records))) - math.pi / 2
        positions[row["key"]] = (
            graph_width / 2 + math.cos(angle) * 355,
            graph_height / 2 + math.sin(angle) * 220,
        )
    edges = {
        tuple(sorted((row["key"], target)))
        for row in records
        for target in row["connection_keys"]
    }
    graph_edges = "".join(
        f'<line x1="{positions[source][0]:.1f}" y1="{positions[source][1]:.1f}" '
        f'x2="{positions[target][0]:.1f}" y2="{positions[target][1]:.1f}"></line>'
        for source, target in sorted(edges)
    )
    graph_nodes = "".join(
        f'<g class="graph-node record-target" data-key="{html.escape(row["key"], quote=True)}" '
        f'tabindex="0" role="button" aria-label="{html.escape(row["key"], quote=True)}">'
        f'<circle cx="{positions[row["key"]][0]:.1f}" cy="{positions[row["key"]][1]:.1f}" r="9"></circle>'
        f'<text x="{positions[row["key"]][0] + 13:.1f}" y="{positions[row["key"]][1] + 4:.1f}">'
        f'{html.escape(str(row["artist"]))}</text></g>'
        for row in records
    )
    connection_list = "".join(
        f'<li><button class="text-link record-target" data-key="{html.escape(source, quote=True)}">{html.escape(source)}</button>'
        f'<span> connects to </span><button class="text-link record-target" data-key="{html.escape(target, quote=True)}">'
        f"{html.escape(target)}</button></li>"
        for source, target in sorted(edges)
    )

    route_cards = "".join(
        f'<article class="route-card"><span>{len(keys)} stops</span>'
        f'<h3>{html.escape(name.replace("-", " ").title())}</h3>'
        f'<p>{" → ".join(html.escape(key.split(" - ", 1)[0]) for key in keys)}</p>'
        f'<button class="route-start" data-route="{html.escape(name, quote=True)}">Start route</button></article>'
        for name, keys in routes.items()
    )

    gradients = ["#32105d,#092940", "#521234,#27170b", "#073e3c,#171335", "#4a1a13,#30082f", "#253e0c,#1c0b2f"]
    timeline: list[str] = []
    section_blocks: list[str] = []
    for index, section in enumerate(sections, 1):
        heading = str(section["heading"])
        albums = by_section.get(heading, [])
        years = year_range(albums)
        location = era_setting(metadata, "era_locations", heading)
        equipment = era_setting(metadata, "era_equipment", heading)
        caption = era_setting(metadata, "era_captions", heading)
        gradient = era_setting(metadata, "era_gradients", heading, gradients[(index - 1) % len(gradients)])
        timeline.append(
            f'<li><a href="#section-{index}"><span>{html.escape(heading)}</span><small>{html.escape(years)}</small></a></li>'
        )
        paragraphs = "".join(f'<div class="reveal"><p>{value}</p></div>' for value in section["paragraphs"])
        ephemera = ""
        if location or equipment or caption:
            ephemera = f"""<aside class="ephemera reveal" aria-label="Era ephemera">
              <span>Scene fragment / {html.escape(years)}</span>
              <div class="ephemera-grid"><div><small>Location</small><strong>{html.escape(location)}</strong></div>
              <div><small>Machines</small><strong>{html.escape(equipment)}</strong></div></div>
              <p>{html.escape(caption)}</p></aside>"""
        cards = "".join(album_card(row) for row in albums)
        section_blocks.append(
            f"""<div class="era-band" style="--era-gradient:linear-gradient(120deg,{html.escape(gradient, quote=True)})">
            <span>{index:02d}</span><div><small>{html.escape(years)} · {html.escape(location)}</small>
            <h2>{html.escape(heading)}</h2></div></div>
            <section class="story-section" id="section-{index}">
            <div class="story-copy"><span class="eyebrow">Transmission {index:02d}</span>
            <h2>{html.escape(heading)}</h2>{paragraphs}</div>{ephemera}
            <div class="album-grid">{cards}</div></section>"""
        )

    title_text = html.escape(title)
    slug = re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-")
    subtitle = html.escape(str(metadata.get("subtitle", "A long-session listening companion.")))
    hero_label = html.escape(str(metadata.get("hero_label", "Musiculum / long-form listening")))
    hero_copy = "".join(f"<p>{paragraph}</p>" for paragraph in hero_paragraphs)
    texture_options = "".join(
        f'<option value="{html.escape(texture, quote=True)}">{html.escape(texture)}</option>'
        for texture in textures
    )
    inference_note = (
        f'<p>Energy and texture were inferred from the essay text for this guide. '
        f'Add <code>Energy</code>, <code>Texture</code>, <code>Listen for</code> and <code>Connections</code> '
        f'columns to the source tables to set them deliberately.</p>'
        if inferred
        else ""
    )

    css = (ASSETS_DIR / "v3.css").read_text(encoding="utf-8")
    script = (ASSETS_DIR / "v3.js").read_text(encoding="utf-8")
    script = (
        script.replace("__RECORDS__", json.dumps(records, ensure_ascii=False).replace("</", "<\\/"))
        .replace("__ROUTES__", json.dumps(routes, ensure_ascii=False).replace("</", "<\\/"))
        .replace("__STORAGE_KEY__", slug)
        .replace("__TITLE__", title.replace("\\", "\\\\").replace("'", "\\'"))
        .replace("__SLUG__", slug)
    )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{title_text} long-session listening guide"><title>{title_text}</title>
<style>{css}</style></head><body><a class="skip" href="#content">Skip to guide</a><div class="layout">
<aside class="rail"><div class="brand">Musiculum / V3<strong>{title_text}</strong></div>
<nav aria-label="Era timeline"><ol class="timeline">{"".join(timeline)}</ol></nav>
<div class="rail-actions"><button class="btn crate-dig">Crate dig</button><a class="btn" href="#session-notes">Session notes</a></div></aside>
<main class="main" id="content"><header class="hero"><div class="hero-content reveal"><span class="eyebrow">{hero_label}</span>
<h1>{title_text}</h1><p class="subtitle">{subtitle}</p><div class="hero-summary">{hero_copy}</div></div></header>
<nav class="feature-nav" aria-label="Guide tools"><a href="#routes">Listening routes</a><a href="#energy-map">Energy map</a>
<a href="#connections">Connections</a><a href="#session-notes">Notes</a><button class="reset crate-dig">Crate dig</button></nav>
<section class="lab" id="routes"><div class="lab-head"><span class="eyebrow">Curated paths</span>
<h2>Choose a route through the music</h2><p>Each path loads one release at a time into the persistent player.</p></div>
<div class="route-grid">{route_cards}</div></section>
<section class="lab" id="energy-map"><div class="lab-head"><span class="eyebrow">Energy / texture atlas</span>
<h2>Find the pressure you want</h2><p>Records move from lower to higher energy and group by their dominant surface.</p>{inference_note}</div>
<div class="feature-nav" aria-label="Map filters"><label>Artist <input id="artist-filter" type="search" placeholder="Filter artist"></label>
<label>Texture <select id="texture-filter"><option value="">All textures</option>{texture_options}</select></label>
<label>Minimum energy <input id="energy-filter" type="range" min="1" max="10" value="1"></label>
<button class="reset" id="reset-filters">Reset</button><output id="result-count" aria-live="polite"></output></div>
<div class="map-wrap"><svg viewBox="0 0 {map_width} {map_height}" role="img" aria-labelledby="map-title">
<title id="map-title">Energy and texture map of selected releases</title>{map_labels}{"".join(map_points)}</svg></div>
<div class="energy-axis"><span>Lower energy</span><span>Higher energy</span></div></section>
<section class="lab" id="connections"><div class="lab-head"><span class="eyebrow">Signal paths</span>
<h2>Connections across scenes and eras</h2><p>Follow affinities in sound, production method, and historical role.</p></div>
<div class="graph-wrap"><svg viewBox="0 0 {graph_width} {graph_height}" role="img" aria-labelledby="graph-title">
<title id="graph-title">Connections between selected releases</title><g>{graph_edges}</g><g>{graph_nodes}</g></svg></div>
<ul class="connection-list">{connection_list}</ul></section>
{"".join(section_blocks)}
<section class="lab" id="session-notes"><div class="lab-head"><span class="eyebrow">Private listening journal</span>
<h2>Keep what the session reveals</h2><p>Bookmarks and notes stay in this browser. Export them as Markdown.</p></div>
<div class="notes-panel"><div><h3>Saved releases</h3><div class="saved-list" id="saved-list"></div></div>
<div><label for="notes-record">Release</label><select id="notes-record"></select>
<label for="session-note">Your note</label><textarea id="session-note" placeholder="What did you notice?"></textarea>
<div class="notes-actions"><button class="btn" id="export-notes">Export Markdown</button>
<button class="btn" id="clear-notes">Clear saved data</button></div></div></div></section>
<footer class="lab">Built with Musiculum · V3 · {found_count}/{len(records)} Spotify releases resolved</footer></main></div>
<aside class="dock empty" id="dock" aria-label="Listening dock" aria-live="polite"><div class="dock-copy">
<small>Now exploring</small><strong id="dock-artist">Choose a release</strong>
<span id="dock-album">The player loads only when requested.</span><span id="dock-cue"></span></div>
<div class="player-mount" id="player-mount"></div><div class="route-progress" id="route-progress" hidden>
<button class="btn route-prev">Previous</button><span></span><button class="btn route-next">Next</button></div></aside>
<script>{script}</script></body></html>"""
