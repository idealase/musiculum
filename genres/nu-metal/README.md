# Nu-Metal

`first.md` contains the essay and V3 listening metadata. The resolved Spotify catalog is reused when regenerating the long-session page:

```powershell
python fetch_spotify.py nu-metal --reuse-catalog
```

V3 is the default and writes `index.html`. The existing `nu-metal-v3.html` remains as a comparison snapshot.
