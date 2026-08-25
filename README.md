# Musiculum

A Python workflow for turning genre essays in markdown into Spotify-backed HTML listening reports.

## Repository Layout

- `fetch_spotify.py`: CLI pipeline that reads markdown album tables, resolves Spotify album IDs, and builds output artifacts.
- `genres/<genre>/first.md`: source essay markdown for a specific genre.
- `genres/<genre>/spotify_albums.json`: key-value map of `Artist - Album` to Spotify album ID.
- `genres/<genre>/albums_catalog.json`: normalized album catalog with section/year/note + Spotify ID.
- `genres/<genre>/index.html`: generated embeddable listening report.
- `genres/<genre>/share.html`: companion share sheet with the same words and no Spotify embeds.
- `genres/callback.html`: shared Spotify OAuth landing page; every guide redirects through it.
- `genres/_template/`: starter files for adding a new genre.

GitHub Pages deploys the repository root from `main` using `.github/workflows/pages.yml`. The published site redirects
from `/` to the guide hub at `/genres/`; after the first successful workflow run, its URL is shown under the repository's
Actions and Settings -> Pages screens.

## Who Creates What

- You provide `genres/<genre>/first.md`.
- `fetch_spotify.py` generates `spotify_albums.json`, `albums_catalog.json`, `index.html`, and `share.html`.
- You should not hand-author the JSON outputs during normal usage.
- Copilot is optional: use it to help draft/clean your markdown essay and album tables, then run the Python script to generate artifacts.

## End-to-End Flow

1. Create or update `genres/<genre>/first.md`.
2. Run `python fetch_spotify.py <genre>`.
3. Script extracts album rows and V3 listening metadata from markdown tables.
4. Script calls Spotify Search API and resolves album IDs.
5. Script writes:
	- `genres/<genre>/spotify_albums.json`
	- `genres/<genre>/albums_catalog.json`
	- `genres/<genre>/index.html` (V3 long-session listening guide)
	- `genres/<genre>/share.html` (share sheet: no player, no scripts, no network calls)
	- `genres/callback.html` (shared Spotify OAuth landing page)
6. Open `genres/<genre>/index.html` in your browser.

## Requirements

- Python 3.10+
- Spotify API credentials via `.env` in repo root:

```env
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
```

Install optional markdown rendering support:

```bash
pip install -r requirements.txt
```

If `markdown` is not installed, the script still works and will render essay text as a plain `<pre>` block.

## Usage

Run against the default genre (`emo`):

```bash
python fetch_spotify.py
```

Run a specific genre slug under `genres/`:

```bash
python fetch_spotify.py emo
python fetch_spotify.py shoegaze
```

Run a direct folder path:

```bash
python fetch_spotify.py genres/emo
```

Process every genre folder under `genres/` (except folders that start with `_`):

```bash
python fetch_spotify.py --all
```

Agentic workflow (Copilot + script):

1. Ask Copilot to help produce or revise `first.md` for a genre.
2. Ask Copilot to run `python fetch_spotify.py <genre>`.
3. Review generated HTML and, if needed, iterate on markdown content.

Useful options:

```bash
python fetch_spotify.py emo --delay 0.05
python fetch_spotify.py emo --markdown essay.md --html report.html
python fetch_spotify.py emo --share notes.html
python fetch_spotify.py emo --reuse-catalog
python fetch_spotify.py emo --legacy-v1
```

## Sharing a Guide

The guide assumes a Spotify session; the people you send it to usually have neither your server nor your developer app.
Three artifacts cover that gap:

- **`share.html`** — the full essay, era by era, with every note, listening cue, energy and texture, and no iframes,
  scripts, or outbound requests. It opens straight from a `file://` URL, survives being emailed, and prints cleanly.
- **Liner notes** — the playlist panel exports the current selection as Markdown, including the playlist link once one
  exists. Useful for pasting into a message alongside the playlist.
- **A Spotify playlist** — built in the browser with Authorization Code + PKCE, so no client secret is ever in the page.

Playlist export needs a Spotify app of your own:

1. Create an app in the [developer dashboard](https://developer.spotify.com/dashboard).
2. Register the redirect URI the guide displays, character for character. For the published GitHub Pages site it will be
	`https://<account>.github.io/<repository>/genres/callback.html`; every guide shares this one entry. Spotify rejects
	`localhost`, so use `127.0.0.1` only for local development.
3. Paste the client ID into the guide. It is stored in that browser only.

Spotify validates the redirect URI only *after* sign-in, so a mismatch shows up as a Spotify-hosted error page rather
than anything the guide can catch.

A new app is in **development mode**, which Spotify limits to a Premium-account owner plus at most five listeners added
by name and email under *Settings -> User Management*. Anyone else can reach the sign-in screen and is then refused with
a 403. Send those people `share.html` instead.

## Expected Markdown Table Format

The script extracts albums from markdown tables that include at least `Artist` and `Album` columns.

```markdown
| Artist | Album | Year | Why it matters | Listen for | Energy | Texture | Connections |
| --- | --- | --- | --- | --- | ---: | --- | --- |
| Sunny Day Real Estate | Diary | 1994 | Second-wave gateway. | The explosive drum entrances. | 7 | expansive | Mineral - The Power of Failing |
```

Only `Artist` and `Album` are required. V3 also understands `Listen for`, `Energy` (1–10),
`Texture`, and semicolon-separated `Connections`. Column order is flexible because fields
are resolved by header name.

Regenerate the default V3 page without repeating Spotify lookups:

```bash
python fetch_spotify.py emo --reuse-catalog
```

V3 is the default renderer. It uses a single click-to-load Spotify player and adds listening routes, energy/texture
mapping, era ephemera, record connections, crate digging, bookmarks, and browser-local notes.
Use `--legacy-v1` only when intentionally reproducing the original interface.

## Add a New Genre

1. Copy `genres/_template` to `genres/<new-genre>`.
2. Replace `first.md` with your essay and album tables.
3. Run `python fetch_spotify.py <new-genre>`.
4. Open `genres/<new-genre>/index.html`.
