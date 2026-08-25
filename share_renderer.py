"""Renderer for the shareable Musiculum sheet: essay text and album notes, no Spotify embeds."""

from __future__ import annotations

import html
import re
from pathlib import Path

from v3_renderer import (
    album_key,
    era_setting,
    extract_sections,
    infer_missing_fields,
    parse_front_matter,
    section_key,
    year_range,
)

ASSETS_DIR = Path(__file__).resolve().parent / "assets"


def record_entry(position: int, row: dict) -> str:
    artist = html.escape(str(row.get("artist", "")))
    album = html.escape(str(row.get("album", "")))
    year = html.escape(str(row.get("year", "")))
    note = html.escape(str(row.get("note", "")))
    cue = html.escape(str(row.get("listen_for", "")))
    energy = html.escape(str(row.get("energy", "5")))
    texture = html.escape(str(row.get("texture", "unclassified")))
    cue_block = f'<p class="cue"><strong>Listen for</strong>{cue}</p>' if cue else ""
    return (
        f'<li class="record"><div class="record-head"><span>{position:02d} · {artist}</span><span>{year}</span></div>'
        f"<h3>{album}</h3>"
        f'<p class="note">{note}</p>{cue_block}'
        f'<p class="tags">Energy {energy}/10 · {texture}</p></li>'
    )


def render_share(
    title: str,
    markdown_text: str,
    catalog: list[dict],
    found_count: int,
    guide_filename: str = "index.html",
) -> str:
    metadata, essay = parse_front_matter(markdown_text)
    sections = extract_sections(essay)
    summary_paragraphs: list[str] = []
    if sections and str(sections[0]["heading"]).casefold() == "executive summary":
        summary_paragraphs = list(sections.pop(0)["paragraphs"])

    records = [{**row, "key": album_key(row)} for row in catalog]
    infer_missing_fields(records)

    by_section: dict[str, list[dict]] = {}
    for row in records:
        by_section.setdefault(section_key(str(row.get("section", "General"))), []).append(row)

    contents: list[str] = []
    era_blocks: list[str] = []
    position = 0
    for index, section in enumerate(sections, 1):
        heading = str(section["heading"])
        albums = by_section.get(section_key(heading), [])
        years = year_range(albums)
        location = era_setting(metadata, "era_locations", heading)
        equipment = era_setting(metadata, "era_equipment", heading)
        caption = era_setting(metadata, "era_captions", heading)
        meta_parts = [part for part in (years, location, equipment) if part]
        contents.append(
            f'<li><a href="#era-{index}">{html.escape(heading)}</a>'
            f'<small> — {html.escape(years)} · {len(albums)} releases</small></li>'
        )
        paragraphs = "".join(f"<p>{paragraph}</p>" for paragraph in section["paragraphs"])
        caption_block = f'<p class="era-caption">{html.escape(caption)}</p>' if caption else ""
        entries = ""
        if albums:
            items = []
            for row in albums:
                position += 1
                items.append(record_entry(position, row))
            entries = f'<ol class="records">{"".join(items)}</ol>'
        era_blocks.append(
            f'<section class="era" id="era-{index}"><p class="era-index">{index:02d}</p>'
            f"<h2>{html.escape(heading)}</h2>"
            f'<p class="era-meta">{html.escape(" · ".join(meta_parts))}</p>'
            f'<div class="era-body">{paragraphs}</div>{caption_block}{entries}</section>'
        )

    title_text = html.escape(title)
    subtitle = html.escape(str(metadata.get("subtitle", "A long-session listening companion.")))
    summary = "".join(f"<p>{paragraph}</p>" for paragraph in summary_paragraphs)
    playlist_url = str(metadata.get("playlist_url", "")).strip()
    playlist_link = ""
    if re.fullmatch(r"https://(open|play)\.spotify\.com/[\w\-/?=&.]+", playlist_url):
        playlist_link = (
            f'<a class="playlist-link" href="{html.escape(playlist_url, quote=True)}" '
            f'target="_blank" rel="noopener">Listen to the companion playlist →</a>'
        )
    css = (ASSETS_DIR / "share.css").read_text(encoding="utf-8")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{title_text} — shareable listening notes"><title>{title_text} — listening notes</title>
<style>{css}</style></head><body><article class="sheet">
<header><p class="eyebrow">Musiculum / shareable listening notes</p><h1>{title_text}</h1>
<p class="subtitle">{subtitle}</p>
<p class="sheet-meta"><span>{len(records)} releases</span><span>{len(sections)} eras</span><span>No account needed</span></p>
<div class="summary">{summary}</div>{playlist_link}</header>
<nav class="contents" aria-label="Contents"><h2>What is inside</h2><ol>{"".join(contents)}</ol></nav>
{"".join(era_blocks)}
<footer class="sheet-footer">Built with Musiculum. This sheet is plain text and needs no Spotify account — every record is listed
by artist, album and year so it can be found on any service. The full guide with players lives in
<a href="{html.escape(guide_filename, quote=True)}">{html.escape(guide_filename)}</a>
({found_count}/{len(records)} releases matched on Spotify).</footer>
</article></body></html>"""
