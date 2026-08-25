---
name: musiculum
description: 'Convert a markdown music essay into a V3 dark-themed long-session listening guide with a click-to-load Spotify player, listening cues, maps, connections, and notes. Use when: generate music report, build listening guide, convert essay to HTML, create genre page, musiculum, Spotify embeds, album recommendations page, music history HTML.'
argument-hint: 'Provide a genre slug (e.g. emo, triphop) or path to a genre folder'
---

# Musiculum — Music Essay → HTML Listening Guide

Convert a markdown genre essay with album recommendation tables into the V3 long-session listening guide. V3 is always the default; use V1 only when the user explicitly requests the legacy interface.

## When to Use

- User supplies a music essay markdown file and wants it converted into an HTML listening guide
- User wants to generate or regenerate the HTML report for an existing genre folder
- User wants to process all genre folders in the repo
- User says "musiculum", "build listening guide", "generate report", or "convert essay"

## What This Skill Does NOT Do

- **Write the essay.** The user supplies `first.md` — it may come from their own writing, another AI, research, etc. The skill's job is to convert it, not author it.
- If the user asks for help drafting an essay, that's a separate task outside this skill.

## Prerequisites

- `.env` file at repo root with `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`
- Python 3.10+ available
- The essay markdown must contain tables with `Artist` and `Album` columns

## Repository Structure

```
musiculum/
├── .env                          # Spotify credentials (not committed)
├── fetch_spotify.py              # CLI pipeline script
├── genres/
│   ├── _template/                # Starter files for new genres
│   │   ├── first.md
│   │   └── README.md
│   ├── emo/
│   │   ├── first.md              # Source essay (user-authored)
│   │   ├── spotify_albums.json   # Generated: artist→album ID map
│   │   ├── albums_catalog.json   # Generated: full metadata + IDs
│   │   ├── index.html            # Generated: final HTML report
│   │   └── share.html            # Generated: share sheet, no Spotify embeds
│   ├── callback.html             # Generated: shared Spotify OAuth landing page
│   └── <other-genre>/
```

## Procedure

### A. Set up a new genre folder

1. Copy `genres/_template` to `genres/<new-genre>/`.
2. The user places their essay markdown into `genres/<new-genre>/first.md`. The essay should contain narrative text and markdown tables with album recommendations.
3. Verify tables use this format:

```markdown
| Artist | Album | Year | Why it matters | Listen for | Energy | Texture | Connections |
| --- | --- | --- | --- | --- | ---: | --- | --- |
| Sunny Day Real Estate | Diary | 1994 | Second-wave gateway. | The explosive drum entrances. | 7 | expansive | Mineral - The Power of Failing |
```

### B. Generate the HTML report

Run the pipeline script:

```bash
python fetch_spotify.py <genre-slug>
```

This will:
1. Parse `first.md` and extract all albums from markdown tables
2. Authenticate with Spotify via Client Credentials flow
3. Search for each album and resolve Spotify album IDs
4. Write `spotify_albums.json` (flat ID map)
5. Write `albums_catalog.json` (full metadata per album)
6. Write `index.html` using the V3 renderer
7. Write `share.html` using the share renderer

To regenerate visuals while preserving resolved Spotify IDs:

```bash
python fetch_spotify.py <genre-slug> --reuse-catalog
```

### C. Process all genres at once

```bash
python fetch_spotify.py --all
```

### D. Verify

Open `genres/<genre>/index.html` in the browser to preview.

## HTML Report Design Spec

The generated HTML report uses the V3 long-session design:

### Visual Design
- **Dark moody palette**: `#0a0a0c` background, warm amber/copper accents (`#e8c8a0`, `#c0785a`, `#c9a96e`)
- **Typography**: Serif body (Georgia), sans-serif headings (Helvetica Neue), monospace accents
- **Custom scrollbar**, copper text selection highlight
- **Vinyl/zine-inspired** warmth — NOT cold tech dark mode

### Layout & Navigation
- **Sticky sidebar timeline**: Lists all essay sections/eras with year ranges, highlights current section on scroll
- **Full-screen hero**: Title + subtitle + scroll-down hint with pulse animation
- **Era dividers**: Full-width parallax-capable section breaks between eras with gradient backgrounds
- **Responsive**: Sidebar hides on mobile, grid goes single-column

### Content Presentation
- **Narrative prose**: Rendered as styled paragraphs within max-width containers
- **Single persistent listening dock**: The page begins with zero iframes. A user action loads one Spotify player; selecting another release replaces it.
- **Album card grids**: Responsive grids of cards, each containing:
  - Artist name (uppercase, small, muted)
  - Album title (bold, amber)
  - Year (monospace, dark)
  - Listening note (small, muted)
  - A specific `Listen for` cue
  - Energy and texture tags
  - Load-player and bookmark controls
- Cards have hover lift effect with top accent line reveal

### Interactive Features
- **Scroll-reveal animations**: Elements use IntersectionObserver to fade/slide in
  - `.reveal` — fade up (default)
  - `.reveal.from-left` — slide from left
  - `.reveal.from-right` — slide from right
  - `.reveal.scale-in` — scale up from 92%
- **Staggered card reveals**: Album cards cascade in with incremental `transition-delay`
- **Parallax-lite**: Era divider backgrounds shift subtly on scroll
- **Respects `prefers-reduced-motion`**
- **Listening routes**: Curated album sequences with previous/next controls
- **Energy/texture map** and **connections graph**
- **Crate dig** discovery that avoids recently selected records
- **Browser-local bookmarks and session notes** with Markdown export

### Spotify Embeds
- The initial page contains zero Spotify iframes.
- Load a player only after explicit user interaction.
- Keep exactly one iframe in the persistent dock and replace it on selection.
- Use dark theme, lazy loading, and the existing Spotify album IDs.

### Sharing
Three artifacts let a guide travel to someone who has neither the server nor the developer app:

- **Playlist export** (`#playlist`): Authorization Code with PKCE, entirely in the browser, so no client secret
  reaches the page. Scope selector (all / filtered / bookmarked), whole albums or opening tracks only. Guides redirect
  through the shared `genres/callback.html`, which stores the result in `sessionStorage`, verifies the return URL is
  same-origin, and bounces back to the originating guide — so Spotify needs only one registered redirect URI per host.
- **Liner notes**: exports the current selection as Markdown — era headings, numbered releases, notes, cues, energy
  and texture — plus the playlist link once one has been built. Works without any Spotify sign-in.
- **`share.html`**: the same essay and records with no iframes, no scripts, and no outbound requests. Opens from a
  `file://` URL, prints cleanly, and is the right thing to send to anyone outside the developer app's allowlist.

Spotify keeps new apps in **development mode**: the owner needs Premium, and at most five other listeners work, each
added under *Settings -> User Management*. Non-allowlisted accounts reach the sign-in screen and then get a 403.

### Sections Structure
For each `## Heading` in the markdown:
1. Era divider with gradient, heading, range, and optional location
2. Narrative section
3. Optional era ephemera (location, equipment, caption)
4. Album-card grid with cues, energy, texture, and connections

### Reference Implementation
See [the emo genre page](./references/design-reference.md) for the complete HTML/CSS/JS reference.

## Common Options

```bash
python fetch_spotify.py emo                           # Single genre
python fetch_spotify.py --all                         # All genres
python fetch_spotify.py emo --delay 0.05              # Faster API calls
python fetch_spotify.py emo --markdown essay.md       # Custom input filename
python fetch_spotify.py emo --html report.html        # Custom output filename
python fetch_spotify.py emo --share notes.html        # Custom share sheet filename
python fetch_spotify.py emo --reuse-catalog            # Regenerate V3 without Spotify searches
python fetch_spotify.py emo --legacy-v1                # Explicit legacy interface
```

## Troubleshooting

- **"Missing SPOTIFY_CLIENT_ID"**: Ensure `.env` exists at repo root with valid credentials
- **Rate limiting**: The script handles 429s automatically with backoff; reduce `--delay` if too slow
- **"No markdown album table rows found"**: Ensure tables have `Artist` and `Album` in the header row
- **Missing `markdown` package**: Install with `pip install markdown` for rich essay rendering; without it, essay renders as `<pre>` block
- **`redirect_uri: Not matching configuration`**: The address shown in the guide's setup panel is not registered on the
  Spotify app. Add it verbatim, press Add *and* Save, and use `127.0.0.1` rather than `localhost`. Spotify only checks
  this *after* sign-in, so the error appears on a Spotify page rather than in the guide
- **A Spotify-hosted error page with only a help link**: an app-level problem, not a page problem — development mode
  requires the owner to have Premium, and every other listener to be on the allowlist
- **Wrong album resolved**: `search_album` scores candidates on title, artist, type, and year proximity, and prints
  `[weak match]` below a threshold. Check those lines, and confirm the release exists on Spotify before assuming a bug
