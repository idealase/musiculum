# Acid Techno

`first.md` is the source essay and recommendation list for this guide.

Generate the listening page and Spotify metadata from the repository root:

```bash
python fetch_spotify.py acid-techno
```

Regenerate the default V3 interface from the same 24 resolved Spotify releases:

```bash
python fetch_spotify.py acid-techno --reuse-catalog
```

The existing `acid-techno-v2.html` and `acid-techno-v3.html` files remain as comparison snapshots.
