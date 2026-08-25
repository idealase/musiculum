"""Source renderer for Musiculum's default long-session V3 interface."""

from __future__ import annotations

import html
import json
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


def js_string(value: str) -> str:
    """Escape essay text for a single-quoted JS literal inside an inline <script>."""
    return value.replace("\\", "\\\\").replace("'", "\\'").replace("</", "<\\/")


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


def section_key(heading: str) -> str:
    normalized = heading.replace("’", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", normalized).strip().casefold()


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
        "explosive", "relentless", "churning", "assertive", "fractured", "grimy", "turbulent", "riotous",
    ),
    "atmospheric": (
        "reverb", "ambient", "haze", "dream", "gauze", "gauzy", "ethereal", "shimmer", "blur", "cloud",
        "wash", "narcotic", "gossamer", "drone", "laptop", "glitch", "process", "synth", "abstract",
        "granular", "electronic", "shoegaze", "smear", "veil", "submerg",
        "hypnotic", "languid", "cinematic", "murky", "panoramic", "fluid", "shape-shifting", "woozy",
    ),
    "cavernous": (
        "vast", "cathedral", "echo", "sprawl", "epic", "monument", "immense", "expansive", "crescendo",
        "cavern", "architect", "instrumental", "orchestral", "symphon", "swell", "expanse", "immersi",
        "post-rock", "post rock",
        "monumental", "plush", "rounded", "woven", "organic",
    ),
    "crystalline": (
        "clean", "bright", "precise", "delicate", "chime", "pristine", "clarity", "glassy", "melod",
        "gleam", "composition", "classical", "chamber", "arrange", "piano", "string", "formal",
        "intricate", "filigree",
        "glossy", "immaculate", "lacquered", "crisp", "polished", "sleek", "hyperreal",
    ),
    "propulsive": (
        "rhythm", "drive", "motorik", "groove", "pulse", "momentum", "kinetic", "percussi", "drum",
        "funk", "velocity", "propuls", "math", "angular", "geometr", "polyrhythm", "syncopat",
        "krautrock", "jazz", "insistent",
        "shuffled", "swung", "loping", "locked", "elastic", "interlocking", "buoyant", "kinetic",
        "uneven", "greasy", "lurching", "wonky", "rubbery", "muscular", "mechanised", "jittery",
        "limber", "rolling", "virtuosic", "conversational",
    ),
    "spare": (
        "minimal", "quiet", "sparse", "silence", "restraint", "hushed", "austere", "acoustic", "fragile",
        "still", "empty", "spare", "tape", "lo-fi", "bedroom", "field record", "unadorned", "reduc",
        "understat", "stark",
        "slack", "sketched", "unhurried",
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


def texture_family(row: dict) -> str:
    """Group free-form editorial textures into stable lanes without discarding their wording."""
    source = f"{row.get('texture', '')} {row.get('note', '')} {row.get('listen_for', '')}".casefold()
    family = infer_texture(source)
    return "other" if family == "unclassified" else family


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
        row["texture_family"] = texture_family(row)

    by_section: dict[str, list[dict]] = {}
    for row in records:
        by_section.setdefault(section_key(str(row.get("section", "General"))), []).append(row)
    section_order = {section: index for index, section in enumerate(by_section)}

    for row in records:
        if row.get("connections"):
            continue
        peers = by_section[section_key(str(row.get("section", "General")))]
        position = peers.index(row)
        links = [peers[(position + 1) % len(peers)]["key"]] if len(peers) > 1 else []
        cross_candidates = [other for other in records if other.get("section") != row.get("section")]
        if cross_candidates:
            source_section = section_order[section_key(str(row.get("section", "General")))]
            cross = min(
                cross_candidates,
                key=lambda other: (
                    0 if other["texture_family"] == row["texture_family"] else 1,
                    abs(int(str(other.get("energy", "5"))) - int(str(row.get("energy", "5")))),
                    abs(section_order[section_key(str(other.get("section", "General")))] - source_section),
                ),
            )
            if cross["key"] not in links:
                links.append(cross["key"])
        row["connections"] = "; ".join(dict.fromkeys(link for link in links if link != row["key"]))
    return touched


def connection_reason(source: dict, target: dict) -> str:
    if source.get("section") == target.get("section"):
        return "Within-era relay"
    if source.get("texture") == target.get("texture"):
        return f"Shared {source.get('texture', 'surface')} texture"
    if source.get("texture_family") == target.get("texture_family"):
        return f"Shared {source.get('texture_family', 'sonic')} family"
    energy_delta = abs(int(str(source.get("energy", "5"))) - int(str(target.get("energy", "5"))))
    return f"Cross-era affinity · energy shift {energy_delta}"


def render_v3(
    title: str,
    markdown_text: str,
    catalog: list[dict],
    found_count: int,
    share_filename: str = "share.html",
) -> str:
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
        by_section.setdefault(section_key(str(row.get("section", "General"))), []).append(row)

    family_order = ["spare", "crystalline", "atmospheric", "cavernous", "propulsive", "abrasive", "other"]
    texture_families = [family for family in family_order if any(row["texture_family"] == family for row in records)]
    for row in records:
        energy = int(str(row.get("energy", "5")))
        if not 1 <= energy <= 10:
            raise ValueError(f"Energy must be 1–10: {row['key']}")

    atlas_header = "".join(f"<span>{energy}</span>" for energy in range(1, 11))
    atlas_rows: list[str] = []
    for family in texture_families:
        cells: list[str] = []
        for energy in range(1, 11):
            bucket = [
                row for row in records
                if row["texture_family"] == family and int(str(row.get("energy", "5"))) == energy
            ]
            chips = "".join(
                f'<button class="atlas-record record-target" data-key="{html.escape(row["key"], quote=True)}" '
                f'title="{html.escape(row["key"], quote=True)} · {html.escape(str(row.get("texture", "")), quote=True)}">'
                f'<strong>{html.escape(str(row["artist"]))}</strong><span>{html.escape(str(row["album"]))}</span>'
                f'<small>{html.escape(str(row.get("year", "")))} · {html.escape(str(row.get("texture", "")))}</small></button>'
                for row in bucket
            )
            cells.append(f'<div class="atlas-cell" data-energy="{energy}">{chips}</div>')
        atlas_rows.append(
            f'<div class="atlas-row"><div class="atlas-label"><strong>{html.escape(family)}</strong>'
            f'<small>{sum(1 for row in records if row["texture_family"] == family)} releases</small></div>{"".join(cells)}</div>'
        )

    edges = {
        tuple(sorted((row["key"], target)))
        for row in records
        for target in row["connection_keys"]
    }
    record_by_key = {row["key"]: row for row in records}
    scene_names = [str(section["heading"]) for section in sections if by_section.get(section_key(str(section["heading"])))]
    scene_index = {section_key(name): index for index, name in enumerate(scene_names)}
    scene_edges: dict[tuple[str, str], int] = {}
    cross_edges: list[tuple[str, str]] = []
    for source, target in sorted(edges):
        source_scene = section_key(str(record_by_key[source].get("section", "General")))
        target_scene = section_key(str(record_by_key[target].get("section", "General")))
        if source_scene == target_scene or source_scene not in scene_index or target_scene not in scene_index:
            continue
        pair = tuple(sorted((source_scene, target_scene), key=scene_index.get))
        scene_edges[pair] = scene_edges.get(pair, 0) + 1
        cross_edges.append((source, target))

    graph_width, graph_height = max(920, len(scene_names) * 155), 430
    graph_y = 300
    graph_positions = {
        section_key(scene): 75 + index * ((graph_width - 150) / max(1, len(scene_names) - 1))
        for index, scene in enumerate(scene_names)
    }
    graph_paths: list[str] = []
    for (source_scene, target_scene), count in scene_edges.items():
        source_x, target_x = graph_positions[source_scene], graph_positions[target_scene]
        span = max(1, scene_index[target_scene] - scene_index[source_scene])
        control_y = graph_y - 48 - span * 25
        midpoint_x = (source_x + target_x) / 2
        label_y = (graph_y + control_y) / 2 - 5
        graph_paths.append(
            f'<path d="M {source_x:.1f} {graph_y} Q {midpoint_x:.1f} {control_y:.1f} {target_x:.1f} {graph_y}" '
            f'style="--signal-weight:{min(6, 1 + count / 3):.1f}"><title>{html.escape(source_scene)} → '
            f'{html.escape(target_scene)}: {count} paths</title></path><text class="edge-count" x="{midpoint_x:.1f}" '
            f'y="{label_y:.1f}">{count}</text>'
        )
    graph_nodes = "".join(
        f'<g class="scene-node"><circle cx="{graph_positions[section_key(scene)]:.1f}" cy="{graph_y}" r="22"></circle>'
        f'<text x="{graph_positions[section_key(scene)]:.1f}" y="{graph_y + 4}" text-anchor="middle">{index + 1:02d}</text>'
        f'<text class="scene-year" x="{graph_positions[section_key(scene)]:.1f}" y="{graph_y + 43}" text-anchor="middle">'
        f'{html.escape(year_range(by_section[section_key(scene)]))}</text></g>'
        for index, scene in enumerate(scene_names)
    )
    scene_key = "".join(
        f'<article><span>{index + 1:02d}</span><div><strong>{html.escape(scene)}</strong>'
        f'<small>{html.escape(year_range(by_section[section_key(scene)]))} · {len(by_section[section_key(scene)])} releases · '
        f'{len({row["texture_family"] for row in by_section[section_key(scene)]})} texture families</small></div></article>'
        for index, scene in enumerate(scene_names)
    )
    connection_list = "".join(
        f'<li class="connection-card"><div><span class="signal-era">Era {scene_index[section_key(str(record_by_key[source]["section"]))] + 1:02d}'
        f' → {scene_index[section_key(str(record_by_key[target]["section"]))] + 1:02d}</span>'
        f'<strong>{html.escape(connection_reason(record_by_key[source], record_by_key[target]))}</strong></div>'
        f'<button class="text-link record-target" data-key="{html.escape(source, quote=True)}">{html.escape(source)}</button>'
        f'<span aria-hidden="true">→</span><button class="text-link record-target" data-key="{html.escape(target, quote=True)}">'
        f'{html.escape(target)}</button></li>'
        for source, target in cross_edges
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
        albums = by_section.get(section_key(heading), [])
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
        featured = next((row for row in albums if row.get("spotify_id")), None)
        featured_player = ""
        if featured:
            featured_player = f"""<aside class="era-feature reveal" aria-label="Featured release for {html.escape(heading, quote=True)}">
              <div><span class="eyebrow">First suggestion / ready to play</span>
              <h3>{html.escape(str(featured["artist"]))} — {html.escape(str(featured["album"]))}</h3>
              <p>{html.escape(str(featured.get("listen_for") or featured.get("note") or ""))}</p></div>
              <iframe title="{html.escape(featured["key"], quote=True)}" src="https://open.spotify.com/embed/album/{html.escape(str(featured["spotify_id"]), quote=True)}?utm_source=generator&theme=0"
              allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" loading="lazy"></iframe></aside>"""
        section_blocks.append(
            f"""<div class="era-band" style="--era-gradient:linear-gradient(120deg,{html.escape(gradient, quote=True)})">
            <span>{index:02d}</span><div><small>{html.escape(years)} · {html.escape(location)}</small>
            <h2>{html.escape(heading)}</h2></div></div>
            <section class="story-section" id="section-{index}">
            <div class="story-copy"><span class="eyebrow">Transmission {index:02d}</span>
            <h2>{html.escape(heading)}</h2>{paragraphs}</div>{ephemera}{featured_player}
            <div class="album-grid">{cards}</div></section>"""
        )

    title_text = html.escape(title)
    slug = re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-")
    subtitle_text = str(metadata.get("subtitle", "A long-session listening companion."))
    subtitle = html.escape(subtitle_text)
    hero_label = html.escape(str(metadata.get("hero_label", "Musiculum / long-form listening")))
    playlist_name = html.escape(f"{title} · Musiculum", quote=True)
    share_href = html.escape(share_filename, quote=True)
    share_label = html.escape(f"{share_filename} — the same guide with no Spotify embeds")
    hero_copy = "".join(f"<p>{paragraph}</p>" for paragraph in hero_paragraphs)
    texture_options = "".join(
        f'<option value="{html.escape(family, quote=True)}">{html.escape(family)}</option>'
        for family in texture_families
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
        .replace("__TITLE__", js_string(title))
        .replace("__SUBTITLE__", js_string(subtitle_text))
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
<a href="#connections">Connections</a><a href="#playlist">Playlist</a><a href="#session-notes">Notes</a><a href="{share_href}">Share sheet</a><button class="reset crate-dig">Crate dig</button></nav>
<section class="lab" id="routes"><div class="lab-head"><span class="eyebrow">Curated paths</span>
<h2>Choose a route through the music</h2><p>Each path loads one release at a time into the persistent player.</p></div>
<div class="route-grid">{route_cards}</div></section>
<section class="lab" id="energy-map"><div class="lab-head"><span class="eyebrow">Energy / texture atlas</span>
<h2>Find the pressure you want</h2><p>Records move from lower to higher energy and group by their dominant surface.</p>{inference_note}</div>
<div class="feature-nav" aria-label="Map filters"><label>Artist <input id="artist-filter" type="search" placeholder="Filter artist"></label>
<label>Texture <select id="texture-filter"><option value="">All textures</option>{texture_options}</select></label>
<label>Minimum energy <input id="energy-filter" type="range" min="1" max="10" value="1"></label>
<button class="reset" id="reset-filters">Reset</button><output id="result-count" aria-live="polite"></output></div>
<div class="atlas-wrap" role="region" aria-label="Energy and texture atlas"><div class="atlas">
<div class="atlas-scale"><span>Texture family</span>{atlas_header}</div>{"".join(atlas_rows)}</div></div>
<div class="energy-axis"><span>Lower energy</span><span>Higher energy</span></div></section>
<section class="lab" id="connections"><div class="lab-head"><span class="eyebrow">Signal paths</span>
<h2>Connections across scenes and eras</h2><p>Arc weight shows how many record-level paths bridge two eras. Select any detailed path below to hear either endpoint.</p></div>
<div class="graph-wrap"><svg viewBox="0 0 {graph_width} {graph_height}" role="img" aria-labelledby="graph-title">
<title id="graph-title">Chronological connections between eras</title><line class="signal-baseline" x1="50" y1="{graph_y}" x2="{graph_width - 50}" y2="{graph_y}"></line>
<g class="signal-arcs">{"".join(graph_paths)}</g><g>{graph_nodes}</g></svg></div>
<div class="scene-key">{scene_key}</div>
<ul class="connection-list">{connection_list}</ul></section>
{"".join(section_blocks)}
<section class="lab" id="playlist"><div class="lab-head"><span class="eyebrow">Export to Spotify</span>
<h2>Turn this guide into a playlist</h2><p>Sign in with your own Spotify account and build a playlist from these {len(records)} releases.
The sign-in runs entirely in this browser using PKCE, so no secret is stored in the page and nothing is sent to a server other than Spotify.</p></div>
<div class="playlist-panel"><div class="playlist-form">
<label for="playlist-name">Playlist name</label><input id="playlist-name" type="text" value="{playlist_name}">
<label for="playlist-scope">Which records</label><select id="playlist-scope">
<option value="all">Every release in this guide ({len(records)})</option>
<option value="filtered">Whatever the energy map filters currently show</option>
<option value="bookmarks">Bookmarked releases only</option></select>
<label for="playlist-depth">How much of each</label><select id="playlist-depth">
<option value="album">Every track, album by album</option>
<option value="single">Opening track only</option></select>
<label class="playlist-check"><input id="playlist-public" type="checkbox"> Make the playlist public</label>
<button class="btn playlist-send" id="playlist-send">Send to Spotify</button></div>
<div class="playlist-setup"><label for="playlist-client">Your Spotify app client ID</label>
<input id="playlist-client" type="text" placeholder="Client ID from your Spotify app" autocomplete="off" spellcheck="false">
<p>Create an app in the <a href="https://developer.spotify.com/dashboard" target="_blank" rel="noopener">Spotify developer dashboard</a>,
register the redirect URI below against it, then paste the client ID here. It is kept in this browser only, and no client secret is needed.</p>
<p>Redirect URI to register: <code id="playlist-redirect"></code>
<button class="btn btn-inline" id="playlist-redirect-copy">Copy</button></p>
<p>Spotify matches this character for character. Paste it into <em>Edit settings &rarr; Redirect URIs</em>, press Add, then Save.
A different port or <code>localhost</code> instead of <code>127.0.0.1</code> produces <em>redirect_uri: Not matching configuration</em>,
and Spotify only reports it after you have signed in. Every guide on this address shares this one entry, so you only register it once.</p>
<p>Spotify only accepts HTTPS or loopback addresses, so serve the guide with something like <code>python -m http.server 8000 --bind 127.0.0.1</code> rather than opening the file directly.</p>
<p>If Spotify shows its own error page with nothing but a help link, the app itself is the problem rather than this guide.
A new app sits in <em>development mode</em>, which requires the owning account to have Spotify Premium, and admits at most five listeners &mdash;
each one added by name and email under <em>Settings &rarr; User Management</em>. An account that signs in without being on that list
gets as far as the sign-in screen and is then refused.</p></div></div>
<output class="playlist-status" id="playlist-status" aria-live="polite">Not connected to Spotify yet.</output>
<div class="liner-share"><div><span class="eyebrow">Send the words with the music</span>
<h3>Liner notes for whoever you share this with</h3>
<p>A playlist arrives without context. This exports the same selection as Markdown — era by era, with every note, listening cue,
energy and texture — and includes the playlist link once you have built one. It works even without a Spotify sign-in.
For a version anyone can open in a browser, send them <a href="{share_href}">{share_label}</a>.</p></div>
<div class="liner-actions"><button class="btn" id="liner-copy">Copy liner notes</button>
<button class="btn" id="liner-download">Download Markdown</button>
<output class="liner-status" id="liner-status" aria-live="polite"></output></div></div></section>
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
