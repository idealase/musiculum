# Musiculum

A personal-first Python workflow for turning genre essays in markdown into Spotify-backed HTML listening reports, with optional static sharing.

## Repository Layout

- `fetch_spotify.py`: CLI pipeline that reads markdown album tables, resolves Spotify album IDs, and builds output artifacts.
- `genres/<genre>/first.md`: source essay markdown for a specific genre.
- `genres/<genre>/spotify_albums.json`: key-value map of `Artist - Album` to Spotify album ID.
- `genres/<genre>/albums_catalog.json`: normalized album catalog with section/year/note + Spotify ID.
- `genres/<genre>/index.html`: generated embeddable listening report.
- `genres/<genre>/share.html`: companion share sheet with the same words and no Spotify embeds.
- `genres/callback.html`: shared Spotify OAuth landing page; every guide redirects through it.
- `genres/spotify-client.js.example`: template for local runtime config of the public Spotify Client ID used by playlist export.
- `genres/_template/`: starter files for adding a new genre.

GitHub Pages deploys the repository root from `main` using `.github/workflows/pages.yml`. The published site redirects
from `/` to the guide hub at `/genres/`; after the first successful workflow run, its URL is shown under the repository's
Actions and Settings -> Pages screens.

During build/deploy, the maintainer injects the Spotify Client ID into each generated `genres/<genre>/index.html` guide
so hosted listeners can authenticate without creating their own Spotify app.

## Operating Model (Personal First, Optional Sharing)

- Musiculum is primarily for one maintainer curating and generating listening guides from markdown.
- The same generated guides can be published as static files (for example on GitHub Pages) and shared with a small allow-listed friend group.
- Spotify OAuth ownership stays with the maintainer: one app, one callback URI per host, one allow list managed in Spotify Developer Dashboard.

## Who Does What

### Maintainer (owner/operator)

- Writes `genres/<genre>/first.md`.
- Runs `fetch_spotify.py` to generate `spotify_albums.json`, `albums_catalog.json`, `index.html`, and `share.html`.
- Owns Spotify app registration, redirect URI setup, and Spotify allow list management.
- Injects the Spotify Client ID during build/deploy for the hosted guide experience.

### End user (allow-listed friend/listener)

- Opens the published guide.
- Authenticates with Spotify when they want playlist export.
- Uses the app; they do **not** create a Spotify developer app or manage callback settings.

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
- Spotify API credentials via `.env` in repo root (maintainer only):

```env
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
```

Install optional markdown rendering support:

```bash
pip install -r requirements.txt
```

If `markdown` is not installed, the script still works and will render essay text as a plain `<pre>` block.

### OAuth and Deployment Ownership (Maintainer)

- App registration in Spotify Developer Dashboard is maintainer-owned.
- The callback URI is maintainer-owned and host-specific (for GitHub Pages: `https://<account>.github.io/<repository>/genres/callback.html`).
- The Spotify allow list (development-mode users) is maintainer-owned under *Settings -> User Management*.
- The public static deployment injects the Spotify Client ID at build/deploy time so end users only sign in and use the guide.

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

The guide assumes a Spotify session; the people you send it to should not need maintainer responsibilities.
Three artifacts cover that gap:

- **`share.html`** — the full essay, era by era, with every note, listening cue, energy and texture, and no iframes,
  scripts, or outbound requests. It opens straight from a `file://` URL, survives being emailed, and prints cleanly.
- **Liner notes** — the playlist panel exports the current selection as Markdown, including the playlist link once one
  exists. Useful for pasting into a message alongside the playlist.
- **A Spotify playlist** — built in the browser with Authorization Code + PKCE, so no client secret is ever in the page.

For hosted sharing, listeners only need to sign in with Spotify. They do **not** create their own app or configure redirect URIs.
Those setup tasks remain with the maintainer.

Spotify validates the redirect URI only *after* sign-in, so a mismatch shows up as a Spotify-hosted error page rather
than anything the guide can catch.

A new app is in **development mode**, which Spotify limits to a Premium-account owner plus at most five listeners added
by name and email under *Settings -> User Management*. Anyone outside that allow list can reach sign-in and is then refused
with a 403. Send those people `share.html` instead.

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
