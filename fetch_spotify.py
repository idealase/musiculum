"""Convert a genre markdown essay into Spotify data + embedded HTML report."""

from __future__ import annotations

import argparse
import base64
import html
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from v3_renderer import render_v3
from share_renderer import render_share

try:
    import markdown
except ImportError:  # Optional dependency at runtime.
    markdown = None

CALLBACK_TEMPLATE = Path(__file__).resolve().parent / "assets" / "callback.html"


def load_env(path: Path) -> None:
    if not path.exists():
        return
    with path.open(encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


def get_token(client_id: str, client_secret: str) -> str:
    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    req = urllib.request.Request(
        "https://accounts.spotify.com/api/token",
        data=b"grant_type=client_credentials",
        headers={
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["access_token"]


def compare_key(value: str) -> str:
    """Reduce a title to a comparable core: no diacritics, punctuation, or edition suffixes."""
    folded = unicodedata.normalize("NFKD", value)
    folded = "".join(char for char in folded if not unicodedata.combining(char))
    folded = re.sub(r"[\(\[].*?[\)\]]", " ", folded.casefold())
    folded = re.sub(r"[^a-z0-9]+", " ", folded)
    return re.sub(r"\s+", " ", folded).strip()


def score_candidate(item: dict, artist: str, album: str, year: str) -> tuple[int, str]:
    """Rank a Spotify search hit so exact reissues beat same-artist near-misses."""
    wanted_album = compare_key(album)
    found_album = compare_key(item.get("name", ""))
    score = 0
    if found_album == wanted_album:
        score += 100
    elif found_album.startswith(wanted_album) or wanted_album.startswith(found_album):
        score += 45
    elif wanted_album in found_album:
        score += 20
    else:
        score -= 40

    wanted_artist = compare_key(artist)
    found_artists = [compare_key(entry.get("name", "")) for entry in item.get("artists", [])]
    if wanted_artist in found_artists:
        score += 50
    elif any(wanted_artist in found or found in wanted_artist for found in found_artists if found):
        score += 25
    else:
        score -= 30

    score += {"album": 12, "compilation": 6}.get(item.get("album_type", ""), 0)
    release_year = str(item.get("release_date", ""))[:4]
    if year.isdigit() and release_year.isdigit():
        score += max(0, 12 - abs(int(release_year) - int(year)))
    return score, release_year


def search_album(token: str, artist: str, album: str, year: str = "") -> str | None:
    def _request(search_query: str, limit: int) -> dict:
        q = urllib.parse.quote(search_query)
        url = f"https://api.spotify.com/v1/search?q={q}&type=album&limit={limit}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return json.loads(resp.read())
            except urllib.error.HTTPError:
                raise
            except (urllib.error.URLError, TimeoutError, ConnectionError) as err:
                if attempt == 2:
                    raise
                print(f"  [retry] {err}")
                time.sleep(2 * (attempt + 1))
        return {}

    candidates: list[dict] = []
    try:
        candidates += _request(f"album:{album} artist:{artist}", 10).get("albums", {}).get("items", [])
    except urllib.error.HTTPError as err:
        if err.code == 429:
            wait = int(err.headers.get("Retry-After", 2))
            print(f"  [rate-limit] waiting {wait}s")
            time.sleep(wait)
            return search_album(token, artist, album, year)
        print(f"  [error] HTTP {err.code}: {artist} - {album}")
        return None

    try:
        candidates += _request(f"{artist} {album}", 10).get("albums", {}).get("items", [])
    except urllib.error.HTTPError:
        pass

    if not candidates:
        return None

    unique = {item["id"]: item for item in candidates if item.get("id")}
    best = max(unique.values(), key=lambda item: score_candidate(item, artist, album, year))
    score, _ = score_candidate(best, artist, album, year)
    if score < 60:
        print(f"  [weak match] {artist} - {album} -> {best['artists'][0]['name']} - {best['name']}")
    return best["id"]


def normalize_cell(value: str) -> str:
    value = value.strip()
    value = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", value)
    value = value.replace("*", "").replace("`", "")
    value = value.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    value = re.sub(r"\s+", " ", value)
    return value.strip(" ,")


def extract_title(markdown_text: str, fallback: str) -> str:
    for line in markdown_text.splitlines():
        if line.startswith("# "):
            return normalize_cell(line[2:])
    return fallback


def extract_albums(markdown_text: str) -> list[dict[str, str]]:
    albums: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    current_section = "General"
    lines = markdown_text.splitlines()
    idx = 0

    while idx < len(lines):
        line = lines[idx].strip()

        if line.startswith("## "):
            current_section = normalize_cell(line[3:])

        is_table_header = line.startswith("|") and "artist" in line.lower() and "album" in line.lower()
        if not is_table_header:
            idx += 1
            continue

        headers = [normalize_cell(part).casefold() for part in line.strip("|").split("|")]
        aliases = {
            "artist": "artist",
            "album": "album",
            "year": "year",
            "why it matters": "note",
            "listening note": "note",
            "note": "note",
            "listen for": "listen_for",
            "energy": "energy",
            "texture": "texture",
            "connections": "connections",
        }
        columns = [aliases.get(header, "") for header in headers]

        idx += 2
        while idx < len(lines) and lines[idx].strip().startswith("|"):
            row = lines[idx].strip()
            cells = [normalize_cell(part) for part in row.strip("|").split("|")]
            values = {
                name: cells[cell_index]
                for cell_index, name in enumerate(columns)
                if name and cell_index < len(cells)
            }
            artist = values.get("artist", "")
            album = values.get("album", "")
            if not artist or not album:
                idx += 1
                continue

            key = (artist.casefold(), album.casefold())
            if key in seen:
                idx += 1
                continue
            seen.add(key)

            energy = values.get("energy", "")
            if energy and (not energy.isdigit() or not 1 <= int(energy) <= 10):
                raise ValueError(f"Energy must be an integer from 1 to 10: {artist} - {album}")

            album_row = {
                "artist": artist,
                "album": album,
                "year": values.get("year", ""),
                "note": values.get("note", ""),
                "section": current_section,
            }
            for optional_field in ("listen_for", "energy", "texture", "connections"):
                if values.get(optional_field):
                    album_row[optional_field] = values[optional_field]
            albums.append(album_row)
            idx += 1

    return albums


def merge_catalog_metadata(catalog: list[dict], source_albums: list[dict[str, str]]) -> list[dict]:
    """Refresh editorial metadata while preserving resolved Spotify IDs."""
    existing = {
        (str(row.get("artist", "")).casefold(), str(row.get("album", "")).casefold()): row
        for row in catalog
    }
    merged: list[dict] = []
    for source in source_albums:
        key = (source["artist"].casefold(), source["album"].casefold())
        resolved = existing.get(key)
        if resolved is None:
            raise ValueError(f"Existing catalog is missing source album: {source['artist']} - {source['album']}")
        merged.append({**resolved, **source})
    if len(merged) != len(catalog):
        raise ValueError("Existing catalog contains albums that are no longer present in the markdown source")
    return merged


def markdown_to_html(markdown_text: str) -> str:
    if markdown:
        return markdown.markdown(markdown_text, extensions=["tables", "fenced_code", "sane_lists"])

    escaped = html.escape(markdown_text)
    return f"<pre>{escaped}</pre>"


def extract_sections(markdown_text: str) -> list[dict]:
    """Parse the markdown into ordered sections with headings and body text (excluding tables)."""
    sections: list[dict] = []
    current: dict | None = None
    lines = markdown_text.splitlines()
    in_table = False
    in_code_block = False
    idx = 0

    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()

        # Track fenced code blocks (``` mermaid, etc.)
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            idx += 1
            continue
        if in_code_block:
            idx += 1
            continue

        # Skip the title line (# heading)
        if stripped.startswith("# ") and not stripped.startswith("## "):
            idx += 1
            continue

        # New section on ## heading
        if stripped.startswith("## "):
            heading = normalize_cell(stripped[3:])
            current = {"heading": heading, "paragraphs": []}
            sections.append(current)
            idx += 1
            continue

        # Skip table rows (header, separator, data)
        if stripped.startswith("|"):
            idx += 1
            continue
        if re.match(r"^\|?\s*[-:]+", stripped):
            idx += 1
            continue

        # Accumulate non-empty lines as paragraphs
        if stripped and current is not None:
            # Convert inline markdown bold/italic to HTML
            para = html.escape(stripped)
            para = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", para)
            para = re.sub(r"\*(.+?)\*", r"<em>\1</em>", para)
            para = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', para)
            current["paragraphs"].append(para)

        idx += 1

    return sections


def extract_year_range(albums: list[dict]) -> str:
    """Extract a year range string from a list of album dicts."""
    years = [int(a["year"]) for a in albums if a.get("year") and a["year"].strip().isdigit()]
    if not years:
        return ""
    mn, mx = min(years), max(years)
    return str(mn) if mn == mx else f"{mn}–{mx}"


def build_album_card(row: dict) -> str:
    artist = html.escape(row["artist"])
    album_name = html.escape(row["album"])
    year = html.escape(row.get("year", ""))
    note = html.escape(row.get("note", ""))
    spotify_id = row.get("spotify_id")

    embed = ""
    if spotify_id:
        embed = (
            f'<div class="spotify-embed"><iframe src="https://open.spotify.com/embed/album/{spotify_id}'
            f'?utm_source=generator&theme=0" height="152" '
            f'allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" '
            f'loading="lazy"></iframe></div>'
        )

    return f"""<div class="album-card">
      <div class="card-artist">{artist}</div>
      <div class="card-album">{album_name}</div>
      <div class="card-year">{year}</div>
      <div class="card-note">{note}</div>
      {embed}
    </div>"""


def build_featured_embed(spotify_id: str, label: str = "Essential Listening") -> str:
    if not spotify_id:
        return ""
    return f"""<div class="featured-album reveal scale-in">
    <div class="feat-label">{html.escape(label)}</div>
    <iframe src="https://open.spotify.com/embed/album/{spotify_id}?utm_source=generator&theme=0"
            height="352" allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
            loading="lazy"></iframe>
  </div>"""


def album_cards_html(catalog: list[dict[str, str]]) -> str:
    return "\n".join(build_album_card(row) for row in catalog)


def render_html_report(title: str, markdown_text: str, catalog: list[dict[str, str]], found_count: int) -> str:
    esc_title = html.escape(title)
    sections = extract_sections(markdown_text)

    # Group catalog albums by section heading
    section_albums: dict[str, list[dict]] = {}
    for row in catalog:
        sec = row.get("section", "General")
        section_albums.setdefault(sec, []).append(row)

    # Build sidebar timeline items and section HTML
    sidebar_items: list[str] = []
    sections_html: list[str] = []

    sidebar_items.append(
        '<li data-section="hero"><a href="#hero">Introduction<span class="era-year">Overview</span></a></li>'
    )

    gradient_angles = [
        "#1a0a0a,#0a0a15", "#0a1015,#15100a", "#100a08,#08101a",
        "#0f0808,#0a0f18", "#120808,#08080f", "#08100a,#0a0810",
        "#0a0a10,#100a0a", "#0d0a0a,#0a0d12", "#100808,#08100a",
    ]

    for sec_idx, section in enumerate(sections, 1):
        heading = section["heading"]
        sec_id = f"section-{sec_idx}"
        albums = section_albums.get(heading, [])
        year_range = extract_year_range(albums)

        # Sidebar entry
        sidebar_items.append(
            f'<li data-section="{sec_id}"><a href="#{sec_id}">{html.escape(heading)}'
            f'<span class="era-year">{html.escape(year_range)}</span></a></li>'
        )

        grad = gradient_angles[sec_idx % len(gradient_angles)]

        # Era divider
        divider = f"""<div class="era-divider">
  <div class="era-bg" style="background:linear-gradient(135deg,{grad})"></div>
  <div style="text-align:center">
    <div class="era-label reveal">{html.escape(heading)}</div>
    <div class="era-years reveal" style="transition-delay:.2s">{html.escape(year_range)}</div>
  </div>
</div>"""

        # Section prose
        paras = "\n".join(f'  <div class="reveal"><p>{p}</p></div>' for p in section["paragraphs"])

        # Featured embed (first album with a spotify_id in this section)
        featured = ""
        for a in albums:
            if a.get("spotify_id"):
                featured = build_featured_embed(a["spotify_id"], "Essential Listening")
                break

        # Album cards grid
        cards = ""
        if albums:
            card_items = "\n    ".join(build_album_card(a) for a in albums)
            cards = f"""
  <h3 class="reveal">Recommended Listening</h3>
  <div class="album-grid stagger reveal">
    {card_items}
  </div>"""

        section_block = f"""{divider}

<section class="section" id="{sec_id}">
  <span class="section-number reveal">Section {sec_idx:02d}</span>
  <h2 class="reveal">{html.escape(heading)}</h2>

{paras}

  {featured}
{cards}
</section>"""
        sections_html.append(section_block)

    sidebar_html = "\n    ".join(sidebar_items)
    body_html = "\n\n".join(sections_html)
    total = len(catalog)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc_title}</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth;font-size:17px}}
body{{font-family:'Georgia','Times New Roman',serif;background:#0a0a0c;color:#d4cfc6;line-height:1.75;overflow-x:hidden}}
::selection{{background:#c0392b;color:#fff}}
::-webkit-scrollbar{{width:6px}}
::-webkit-scrollbar-track{{background:#111}}
::-webkit-scrollbar-thumb{{background:#3a2020;border-radius:3px}}
h1,h2,h3{{font-family:'Helvetica Neue','Arial',sans-serif;font-weight:700;letter-spacing:-.02em}}
h1{{font-size:clamp(2.4rem,6vw,4.2rem);line-height:1.1;color:#f0ebe3}}
h2{{font-size:clamp(1.6rem,4vw,2.6rem);line-height:1.2;color:#e8c8a0;margin-bottom:1rem}}
h3{{font-size:.85rem;color:#c9a96e;margin-bottom:.5rem;text-transform:uppercase;letter-spacing:.08em}}
p{{margin-bottom:1.3rem;max-width:68ch}}
strong{{color:#e8c8a0}}
em{{color:#bfab8a;font-style:italic}}
a{{color:#c0785a;text-decoration:none;border-bottom:1px solid rgba(192,120,90,.3);transition:border-color .3s}}
a:hover{{border-color:#c0785a}}
.page-wrapper{{display:flex;min-height:100vh}}
.sidebar{{position:fixed;top:0;left:0;width:220px;height:100vh;background:linear-gradient(180deg,#0d0d10,#12111a);border-right:1px solid #1e1b28;padding:2rem 1rem;display:flex;flex-direction:column;justify-content:center;z-index:100;overflow-y:auto}}
.sidebar-title{{font-family:'Helvetica Neue','Arial',sans-serif;font-size:.65rem;text-transform:uppercase;letter-spacing:.2em;color:#5a5262;margin-bottom:1.5rem;padding-left:.5rem}}
.timeline{{list-style:none;position:relative;padding-left:1.2rem}}
.timeline::before{{content:'';position:absolute;left:0;top:0;bottom:0;width:2px;background:#1e1b28}}
.timeline li{{position:relative;margin-bottom:1.2rem}}
.timeline li::before{{content:'';position:absolute;left:-1.2rem;top:.45rem;width:8px;height:8px;border-radius:50%;background:#2a2535;border:2px solid #3a3345;transition:all .4s ease}}
.timeline li.active::before{{background:#c0785a;border-color:#e8a87c;box-shadow:0 0 12px rgba(192,120,90,.5)}}
.timeline a{{font-family:'Helvetica Neue','Arial',sans-serif;font-size:.75rem;color:#5a5262;text-decoration:none;border:none;display:block;padding:.15rem 0;transition:color .3s;line-height:1.3}}
.timeline li.active a{{color:#e8c8a0}}
.timeline a:hover{{color:#c0785a}}
.timeline .era-year{{display:block;font-size:.6rem;color:#3a3345;margin-top:.1rem;font-family:monospace}}
.timeline li.active .era-year{{color:#7a6858}}
.main-content{{margin-left:220px;flex:1;min-height:100vh}}
.hero{{min-height:100vh;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;padding:4rem 2rem;background:radial-gradient(ellipse at 50% 80%,rgba(100,30,20,.15) 0%,transparent 60%),radial-gradient(ellipse at 20% 20%,rgba(40,20,60,.2) 0%,transparent 50%),#0a0a0c;position:relative}}
.hero::after{{content:'';position:absolute;bottom:0;left:0;right:0;height:120px;background:linear-gradient(transparent,#0a0a0c)}}
.hero h1{{margin-bottom:1rem}}
.hero .subtitle{{font-size:clamp(.95rem,2vw,1.15rem);color:#7a7268;max-width:55ch;line-height:1.6;font-style:italic}}
.hero .scroll-hint{{margin-top:3rem;font-size:.7rem;text-transform:uppercase;letter-spacing:.25em;color:#3a3535;animation:pulse-down 2s infinite}}
@keyframes pulse-down{{0%,100%{{opacity:.3;transform:translateY(0)}}50%{{opacity:.8;transform:translateY(6px)}}}}
.section{{padding:6rem 3rem 4rem;max-width:900px;margin:0 auto;position:relative}}
.section::before{{content:'';position:absolute;top:0;left:50%;transform:translateX(-50%);width:60px;height:1px;background:linear-gradient(90deg,transparent,#3a2020,transparent)}}
.section-number{{font-family:monospace;font-size:.7rem;color:#3a2020;letter-spacing:.15em;text-transform:uppercase;margin-bottom:.5rem;display:block}}
.album-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1.2rem;margin:2.5rem 0 3rem}}
.album-card{{background:linear-gradient(135deg,#13121a,#0f0e15);border:1px solid #1e1b28;border-radius:8px;padding:1.2rem;transition:transform .4s ease,border-color .4s ease,box-shadow .4s ease;position:relative;overflow:hidden}}
.album-card::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,#c0785a,transparent);opacity:0;transition:opacity .4s}}
.album-card:hover{{transform:translateY(-4px);border-color:#2a2535;box-shadow:0 8px 32px rgba(0,0,0,.4)}}
.album-card:hover::before{{opacity:1}}
.album-card .card-artist{{font-family:'Helvetica Neue','Arial',sans-serif;font-size:.7rem;text-transform:uppercase;letter-spacing:.12em;color:#7a6858;margin-bottom:.2rem}}
.album-card .card-album{{font-size:1.05rem;color:#e8c8a0;font-weight:600;margin-bottom:.15rem;font-family:'Helvetica Neue','Arial',sans-serif}}
.album-card .card-year{{font-family:monospace;font-size:.7rem;color:#3a3345;margin-bottom:.6rem}}
.album-card .card-note{{font-size:.82rem;color:#8a8278;line-height:1.5;margin-bottom:.8rem}}
.album-card .spotify-embed{{border-radius:6px;overflow:hidden;margin-top:.5rem}}
.album-card .spotify-embed iframe{{border:0;width:100%;border-radius:6px}}
.featured-album{{margin:2rem 0 2.5rem;padding:1.5rem;background:linear-gradient(135deg,rgba(100,30,20,.08),rgba(20,18,30,.4));border:1px solid #2a1f2f;border-radius:10px}}
.featured-album .feat-label{{font-family:'Helvetica Neue','Arial',sans-serif;font-size:.6rem;text-transform:uppercase;letter-spacing:.2em;color:#5a4a3a;margin-bottom:.8rem}}
.featured-album iframe{{border:0;width:100%;border-radius:8px}}
.era-divider{{height:40vh;display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden}}
.era-divider .era-bg{{position:absolute;inset:0;background-size:cover;background-position:center;filter:brightness(.2) saturate(.4);transform:scale(1.1);transition:transform 1s ease}}
.era-divider:hover .era-bg{{transform:scale(1.15)}}
.era-divider .era-label{{position:relative;z-index:1;font-family:'Helvetica Neue','Arial',sans-serif;font-size:clamp(1.2rem,3vw,2rem);font-weight:700;color:#f0ebe3;text-transform:uppercase;letter-spacing:.15em;text-shadow:0 2px 20px rgba(0,0,0,.8)}}
.era-divider .era-years{{position:relative;z-index:1;font-family:monospace;font-size:.75rem;color:#7a6858;margin-top:.5rem;letter-spacing:.2em}}
.reveal{{opacity:0;transform:translateY(40px);transition:opacity .8s ease,transform .8s ease}}
.reveal.from-left{{transform:translateX(-40px)}}
.reveal.from-right{{transform:translateX(40px)}}
.reveal.scale-in{{transform:scale(.92);transform-origin:center}}
.reveal.visible{{opacity:1;transform:translateY(0) translateX(0) scale(1)}}
.stagger .album-card{{opacity:0;transform:translateY(30px);transition:opacity .6s ease,transform .6s ease}}
.stagger.visible .album-card{{opacity:1;transform:translateY(0)}}
.stagger.visible .album-card:nth-child(1){{transition-delay:.05s}}
.stagger.visible .album-card:nth-child(2){{transition-delay:.1s}}
.stagger.visible .album-card:nth-child(3){{transition-delay:.15s}}
.stagger.visible .album-card:nth-child(4){{transition-delay:.2s}}
.stagger.visible .album-card:nth-child(5){{transition-delay:.25s}}
.stagger.visible .album-card:nth-child(6){{transition-delay:.3s}}
.stagger.visible .album-card:nth-child(7){{transition-delay:.35s}}
.stagger.visible .album-card:nth-child(8){{transition-delay:.4s}}
.stagger.visible .album-card:nth-child(9){{transition-delay:.45s}}
.stagger.visible .album-card:nth-child(10){{transition-delay:.5s}}
.stagger.visible .album-card:nth-child(n+11){{transition-delay:.55s}}
@media(max-width:768px){{.sidebar{{display:none}}.main-content{{margin-left:0}}.section{{padding:4rem 1.5rem 3rem}}.album-grid{{grid-template-columns:1fr}}}}
@media(min-width:769px) and (max-width:1024px){{.sidebar{{width:180px}}.main-content{{margin-left:180px}}}}
</style>
</head>
<body>
<div class="page-wrapper">

<nav class="sidebar">
  <div class="sidebar-title">{esc_title}</div>
  <ul class="timeline">
    {sidebar_html}
  </ul>
</nav>

<main class="main-content">

<header class="hero" id="hero">
  <h1 class="reveal">{esc_title}</h1>
  <p class="subtitle reveal" style="transition-delay:.2s">A Listening Guide &middot; {found_count}/{total} albums on Spotify</p>
  <div class="scroll-hint reveal" style="transition-delay:.6s">&darr; Scroll to begin</div>
</header>

{body_html}

<footer style="text-align:center;padding:2rem;font-size:.65rem;color:#2a2535;border-top:1px solid #1a1a20">
  Built with Musiculum
</footer>

</main>
</div>

<script>
(function(){{
  var reveals=document.querySelectorAll('.reveal');
  var obs=new IntersectionObserver(function(entries){{
    entries.forEach(function(e){{if(e.isIntersecting)e.target.classList.add('visible')}})
  }},{{threshold:.08,rootMargin:'0px 0px -60px 0px'}});
  reveals.forEach(function(el){{obs.observe(el)}});

  var sections=document.querySelectorAll('[id^="hero"],[id^="section-"]');
  var items=document.querySelectorAll('.timeline li');
  var map={{}};
  items.forEach(function(li){{map[li.dataset.section]=li}});
  var so=new IntersectionObserver(function(entries){{
    entries.forEach(function(e){{
      if(e.isIntersecting){{
        items.forEach(function(li){{li.classList.remove('active')}});
        if(map[e.target.id])map[e.target.id].classList.add('active');
      }}
    }})
  }},{{threshold:.15,rootMargin:'-20% 0px -60% 0px'}});
  sections.forEach(function(s){{so.observe(s)}});

  document.querySelectorAll('.timeline a').forEach(function(a){{
    a.addEventListener('click',function(ev){{
      ev.preventDefault();
      var t=document.querySelector(a.getAttribute('href'));
      if(t)t.scrollIntoView({{behavior:'smooth',block:'start'}});
    }})
  }});

  var dividers=document.querySelectorAll('.era-divider .era-bg');
  if(dividers.length&&!window.matchMedia('(prefers-reduced-motion:reduce)').matches){{
    var ticking=false;
    window.addEventListener('scroll',function(){{
      if(!ticking){{
        requestAnimationFrame(function(){{
          dividers.forEach(function(bg){{
            var r=bg.parentElement.getBoundingClientRect();
            var off=(r.top+r.height/2-window.innerHeight/2)*.12;
            bg.style.transform='scale(1.1) translateY('+off+'px)';
          }});
          ticking=false;
        }});
        ticking=true;
      }}
    }});
  }}
}})();
</script>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Spotify report assets from a genre essay markdown file.")
    parser.add_argument(
        "genre",
        nargs="?",
        default="emo",
        help="Genre slug (resolved under --genres-root) or a direct path to a genre folder.",
    )
    parser.add_argument("--genres-root", default="genres", help="Root folder containing genre subfolders.")
    parser.add_argument("--markdown", default="first.md", help="Markdown essay filename inside each genre folder.")
    parser.add_argument("--html", default="index.html", help="Output HTML report filename.")
    parser.add_argument(
        "--share",
        default="share.html",
        help="Output filename for the shareable sheet with no Spotify embeds.",
    )
    parser.add_argument("--json", default="spotify_albums.json", help="Output Spotify ID map filename.")
    parser.add_argument(
        "--catalog",
        default="albums_catalog.json",
        help="Output album catalog filename with metadata and spotify_id per album.",
    )
    parser.add_argument("--all", action="store_true", help="Process all genre folders under --genres-root.")
    parser.add_argument("--delay", type=float, default=0.1, help="Delay between Spotify API calls in seconds.")
    parser.add_argument(
        "--legacy-v1",
        action="store_true",
        help="Render the original V1 interface instead of the default V3 listening guide.",
    )
    parser.add_argument(
        "--reuse-catalog",
        action="store_true",
        help="Reuse existing Spotify IDs from albums_catalog.json without API requests.",
    )
    return parser.parse_args()


def resolve_genre_path(genre_arg: str, genres_root: str) -> Path:
    direct = Path(genre_arg)
    if direct.exists():
        return direct
    return Path(genres_root) / genre_arg


def write_reports(
    genre_dir: Path,
    args: argparse.Namespace,
    title: str,
    markdown_text: str,
    catalog: list[dict],
    found: int,
) -> list[Path]:
    """Write the interactive guide plus, for V3, the share sheet and shared OAuth callback."""
    html_path = genre_dir / args.html
    if args.legacy_v1:
        html_path.write_text(
            render_html_report(title=title, markdown_text=markdown_text, catalog=catalog, found_count=found),
            encoding="utf-8",
        )
        return [html_path]

    html_path.write_text(
        render_v3(
            title=title,
            markdown_text=markdown_text,
            catalog=catalog,
            found_count=found,
            share_filename=args.share,
        ),
        encoding="utf-8",
    )
    share_path = genre_dir / args.share
    share_path.write_text(
        render_share(
            title=title,
            markdown_text=markdown_text,
            catalog=catalog,
            found_count=found,
            guide_filename=args.html,
        ),
        encoding="utf-8",
    )
    # The guides redirect through one callback beside the genre folders, so Spotify needs a single registered URI.
    callback_path = genre_dir.parent / "callback.html"
    callback_path.write_text(CALLBACK_TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
    return [html_path, share_path, callback_path]


def process_genre(genre_dir: Path, args: argparse.Namespace, token: str | None) -> tuple[int, int]:
    markdown_path = genre_dir / args.markdown
    if not markdown_path.exists():
        print(f"Skipping {genre_dir}: markdown not found ({markdown_path.name})")
        return 0, 0

    markdown_text = markdown_path.read_text(encoding="utf-8")
    title = extract_title(markdown_text, genre_dir.name.title())
    albums = extract_albums(markdown_text)
    if not albums:
        print(f"Skipping {genre_dir}: no markdown album table rows found")
        return 0, 0

    print(f"\nProcessing genre: {genre_dir}")
    print(f"Albums discovered in markdown tables: {len(albums)}")

    if args.reuse_catalog:
        catalog_path = genre_dir / args.catalog
        if not catalog_path.exists():
            raise FileNotFoundError(f"Existing album catalog not found: {catalog_path}")
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        if not isinstance(catalog, list) or not all(isinstance(row, dict) for row in catalog):
            raise ValueError(f"Existing album catalog must be a JSON array of objects: {catalog_path}")
        catalog = merge_catalog_metadata(catalog, albums)
        found = sum(1 for row in catalog if row.get("spotify_id"))
        written = write_reports(genre_dir, args, title, markdown_text, catalog, found)
        print(f"Reused: {found}/{len(catalog)} Spotify IDs from {catalog_path}")
        for path in written:
            print(f"Wrote: {path}")
        return found, len(catalog)

    if token is None:
        raise RuntimeError("A Spotify token is required unless --reuse-catalog is supplied.")

    id_map: dict[str, str | None] = {}
    found = 0

    for index, row in enumerate(albums, 1):
        artist = row["artist"]
        album = row["album"]
        key = f"{artist} - {album}"
        spotify_id = search_album(token, artist, album, str(row.get("year", "")))
        row["spotify_id"] = spotify_id
        id_map[key] = spotify_id
        if spotify_id:
            found += 1
            status = "ok"
        else:
            status = "missing"
        print(f"  [{index:03d}/{len(albums)}] {status}: {key}")
        time.sleep(args.delay)

    json_path = genre_dir / args.json
    catalog_path = genre_dir / args.catalog

    json_path.write_text(json.dumps(id_map, indent=2, ensure_ascii=False), encoding="utf-8")
    catalog_path.write_text(json.dumps(albums, indent=2, ensure_ascii=False), encoding="utf-8")
    written = write_reports(genre_dir, args, title, markdown_text, albums, found)

    print(f"Done: {found}/{len(albums)} Spotify IDs resolved")
    print(f"Wrote: {json_path}")
    print(f"Wrote: {catalog_path}")
    for path in written:
        print(f"Wrote: {path}")
    return found, len(albums)


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent
    token: str | None = None
    if args.reuse_catalog:
        print("Spotify lookup skipped; reusing existing album catalog")
    else:
        load_env(repo_root / ".env")
        client_id = os.environ.get("SPOTIFY_CLIENT_ID")
        client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise RuntimeError("Missing SPOTIFY_CLIENT_ID/SPOTIFY_CLIENT_SECRET in environment or .env")
        token = get_token(client_id, client_secret)
        print("Spotify authentication succeeded")

    if args.all:
        root = Path(args.genres_root)
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError(f"Genres root folder not found: {root}")
        genre_dirs = [p for p in sorted(root.iterdir()) if p.is_dir() and not p.name.startswith("_")]
        if not genre_dirs:
            raise ValueError(f"No genre folders found in: {root}")
    else:
        genre_dir = resolve_genre_path(args.genre, args.genres_root)
        if not genre_dir.exists() or not genre_dir.is_dir():
            raise FileNotFoundError(f"Genre folder not found: {genre_dir}")
        genre_dirs = [genre_dir]

    total_found = 0
    total_albums = 0
    for genre_dir in genre_dirs:
        found, albums = process_genre(genre_dir, args, token)
        total_found += found
        total_albums += albums

    print(f"\nOverall: {total_found}/{total_albums} Spotify IDs resolved")
    if markdown is None:
        print("Tip: install 'markdown' package for richer essay HTML rendering.")


if __name__ == "__main__":
    main()
