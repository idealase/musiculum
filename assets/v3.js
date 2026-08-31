(() => {
  const records = __RECORDS__;
  const routes = __ROUTES__;
  const byKey = new Map(records.map(record => [record.key, record]));
  const storageKey = 'musiculum:__STORAGE_KEY__:v3';
  const emptyState = () => ({ bookmarks: [], notes: {}, recent: [], activeKey: '', route: null });
  let state;
  try { state = { ...emptyState(), ...JSON.parse(localStorage.getItem(storageKey) || '{}') }; }
  catch { state = emptyState(); }
  if (!Array.isArray(state.bookmarks)) state.bookmarks = [];
  if (!Array.isArray(state.recent)) state.recent = [];
  if (!state.notes || typeof state.notes !== 'object') state.notes = {};
  let activeRoute = state.route;
  const save = () => {
    try { localStorage.setItem(storageKey, JSON.stringify(state)); }
    catch { /* Keep the listening session usable when storage is unavailable. */ }
  };
  const dock = document.querySelector('#dock');
  const playerMount = document.querySelector('#player-mount');
  const dockArtist = document.querySelector('#dock-artist');
  const dockAlbum = document.querySelector('#dock-album');
  const dockCue = document.querySelector('#dock-cue');
  const routeProgress = document.querySelector('#route-progress');

  const selectRecord = (key, options = {}) => {
    const record = byKey.get(key);
    if (!record) return;
    playerMount.replaceChildren();
    if (record.spotify_id) {
      const iframe = document.createElement('iframe');
      iframe.title = `${record.artist} - ${record.album}`;
      iframe.src = `https://open.spotify.com/embed/album/${record.spotify_id}?utm_source=generator&theme=0`;
      iframe.allow = 'autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture';
      iframe.loading = 'lazy';
      playerMount.append(iframe);
    }
    dock.classList.remove('empty');
    dockArtist.textContent = record.artist;
    dockAlbum.textContent = record.album;
    dockCue.textContent = record.listen_for || record.note || '';
    state.activeKey = key;
    state.recent = [key, ...state.recent.filter(value => value !== key)].slice(0, 8);
    save();
    document.querySelectorAll('.album-card').forEach(card => card.classList.toggle('selected', card.dataset.key === key));
    notesSelect.value = key;
    loadNote();
    if (!options.keepPosition) document.querySelector(`[data-card-key="${CSS.escape(key)}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    updateRouteProgress();
  };

  const updateRouteProgress = () => {
    if (!activeRoute || !routes[activeRoute.name]) {
      routeProgress.hidden = true;
      return;
    }
    const route = routes[activeRoute.name];
    routeProgress.hidden = false;
    routeProgress.querySelector('span').textContent = `${activeRoute.name.replaceAll('-', ' ')} · ${activeRoute.index + 1}/${route.length}`;
    routeProgress.querySelector('.route-prev').disabled = activeRoute.index === 0;
    routeProgress.querySelector('.route-next').disabled = activeRoute.index >= route.length - 1;
  };

  document.addEventListener('click', event => {
    const target = event.target.closest('.load-player,.record-target');
    if (target) selectRecord(target.dataset.key, { keepPosition: !target.matches('.load-player') });
    const bookmark = event.target.closest('.bookmark');
    if (bookmark) {
      const key = bookmark.dataset.key;
      state.bookmarks = state.bookmarks.includes(key) ? state.bookmarks.filter(value => value !== key) : [...state.bookmarks, key];
      save(); renderBookmarks();
    }
    const routeButton = event.target.closest('.route-start');
    if (routeButton) {
      activeRoute = { name: routeButton.dataset.route, index: 0 };
      state.route = activeRoute; save();
      selectRecord(routes[activeRoute.name][0], { keepPosition: true });
    }
  });
  document.addEventListener('keydown', event => {
    if ((event.key === 'Enter' || event.key === ' ') && event.target.matches('.record-target')) {
      event.preventDefault(); selectRecord(event.target.dataset.key);
    }
  });
  routeProgress.querySelector('.route-prev').addEventListener('click', () => {
    if (activeRoute.index > 0) activeRoute.index -= 1;
    state.route = activeRoute; save(); selectRecord(routes[activeRoute.name][activeRoute.index], { keepPosition: true });
  });
  routeProgress.querySelector('.route-next').addEventListener('click', () => {
    if (activeRoute.index < routes[activeRoute.name].length - 1) activeRoute.index += 1;
    state.route = activeRoute; save(); selectRecord(routes[activeRoute.name][activeRoute.index], { keepPosition: true });
  });

  const artistFilter = document.querySelector('#artist-filter');
  const textureFilter = document.querySelector('#texture-filter');
  const energyFilter = document.querySelector('#energy-filter');
  const visibleRecords = () => records.filter(record =>
    (!artistFilter.value || record.artist.toLocaleLowerCase().includes(artistFilter.value.toLocaleLowerCase())) &&
    (!textureFilter.value || (record.texture_family || 'other') === textureFilter.value) &&
    Number(record.energy || 5) >= Number(energyFilter.value)
  );
  const updateFilters = () => {
    const visible = new Set(visibleRecords().map(record => record.key));
    document.querySelectorAll('.album-card,.atlas-record').forEach(element => {
      const isVisible = visible.has(element.dataset.key);
      element.toggleAttribute('hidden', !isVisible);
      element.style.display = isVisible ? '' : 'none';
    });
    document.querySelector('#result-count').textContent = `${visible.size} of ${records.length} releases`;
  };
  [artistFilter, textureFilter, energyFilter].forEach(control => control.addEventListener('input', updateFilters));
  document.querySelector('#reset-filters').addEventListener('click', () => {
    artistFilter.value = ''; textureFilter.value = ''; energyFilter.value = '1'; updateFilters();
  });
  updateFilters();

  document.querySelectorAll('.crate-dig').forEach(button => button.addEventListener('click', () => {
    const visible = visibleRecords();
    const fresh = visible.filter(record => !state.recent.includes(record.key));
    const pool = fresh.length ? fresh : visible;
    if (!pool.length) return;
    const record = pool[Math.floor(Math.random() * pool.length)];
    selectRecord(record.key);
  }));

  const notesSelect = document.querySelector('#notes-record');
  records.forEach(record => {
    const option = document.createElement('option'); option.value = record.key; option.textContent = record.key; notesSelect.append(option);
  });
  const notesArea = document.querySelector('#session-note');
  const loadNote = () => notesArea.value = state.notes[notesSelect.value] || '';
  notesSelect.addEventListener('change', loadNote);
  notesArea.addEventListener('input', () => {
    if (notesArea.value) state.notes[notesSelect.value] = notesArea.value;
    else delete state.notes[notesSelect.value];
    save();
  });
  const renderBookmarks = () => {
    document.querySelectorAll('.album-card').forEach(card => card.classList.toggle('bookmarked', state.bookmarks.includes(card.dataset.key)));
    document.querySelectorAll('.bookmark').forEach(button => {
      const saved = state.bookmarks.includes(button.dataset.key);
      button.textContent = saved ? '★' : '☆'; button.setAttribute('aria-pressed', String(saved));
    });
    const list = document.querySelector('#saved-list');
    list.replaceChildren();
    state.bookmarks.forEach(key => {
      const item = document.createElement('div'); item.className = 'saved-item';
      const button = document.createElement('button'); button.className = 'text-link record-target'; button.dataset.key = key; button.textContent = key;
      const marker = document.createElement('span'); marker.textContent = state.notes[key] ? 'note saved' : 'bookmarked';
      item.append(button, marker); list.append(item);
    });
    if (!state.bookmarks.length) list.textContent = 'No saved releases yet.';
  };
  document.querySelector('#export-notes').addEventListener('click', () => {
    const lines = ['# __TITLE__ — session notes', ''];
    for (const record of records) {
      if (!state.bookmarks.includes(record.key) && !state.notes[record.key]) continue;
      lines.push(`## ${record.key}`, '', state.notes[record.key] || '_Bookmarked_', '');
    }
    const blob = new Blob([lines.join('\n')], { type: 'text/markdown' });
    const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = '__SLUG__-session-notes.md'; link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  });
  document.querySelector('#clear-notes').addEventListener('click', () => {
    state = { ...emptyState(), recent: state.recent, activeKey: state.activeKey };
    save(); notesArea.value = ''; renderBookmarks();
  });
  if (state.activeKey && byKey.has(state.activeKey)) { notesSelect.value = state.activeKey; }
  loadNote(); renderBookmarks(); updateRouteProgress();

  // Spotify playlist export: Authorization Code with PKCE, so the page needs no client secret and no server.
  const playlistName = document.querySelector('#playlist-name');
  const playlistScope = document.querySelector('#playlist-scope');
  const playlistDepth = document.querySelector('#playlist-depth');
  const playlistPublic = document.querySelector('#playlist-public');
  const playlistSend = document.querySelector('#playlist-send');
  const playlistStatus = document.querySelector('#playlist-status');
  const playlistClientSource = document.querySelector('#playlist-client-source');
  const playlistMaintainerSetup = document.querySelector('#playlist-maintainer-setup');
  const linerCopy = document.querySelector('#liner-copy');
  const linerDownload = document.querySelector('#liner-download');
  const linerStatus = document.querySelector('#liner-status');
  // One redirect URI for every guide on this host, so only a single entry needs registering with Spotify.
  const redirectUri = new URL('../callback.html', location.href).href;
  const pkceKey = 'musiculum:spotify-pkce';
  const returnKey = 'musiculum:spotify-return';
  const resultKey = 'musiculum:spotify-result';
  const intentKey = 'musiculum:spotify-intent:__STORAGE_KEY__';
  let accessToken = '';
  document.querySelector('#playlist-redirect').textContent = redirectUri;
  document.querySelector('#playlist-redirect-copy').addEventListener('click', async event => {
    try { await navigator.clipboard.writeText(redirectUri); event.target.textContent = 'Copied'; }
    catch { event.target.textContent = 'Select it manually'; }
    setTimeout(() => event.target.textContent = 'Copy', 2000);
  });
  const configuredClientId = typeof window.__MUSICULUM_SPOTIFY_CLIENT_ID__ === 'string'
    ? window.__MUSICULUM_SPOTIFY_CLIENT_ID__.trim()
    : '';
  if (configuredClientId) {
    playlistClientSource.textContent = 'Spotify sign-in is ready. The site maintainer owns the app configuration; listeners only need to sign in.';
  } else {
    playlistMaintainerSetup.open = true;
    playlistClientSource.replaceChildren(
      document.createTextNode('Spotify Client ID is not configured. Maintainer setup: create '),
      Object.assign(document.createElement('code'), { textContent: 'genres/spotify-client.js' }),
      document.createTextNode(' for local use, or set the '),
      Object.assign(document.createElement('code'), { textContent: 'SPOTIFY_CLIENT_ID' }),
      document.createTextNode(' GitHub repository variable for Pages deploys.')
    );
  }

  const setPlaylistStatus = (message, isError = false) => {
    playlistStatus.replaceChildren(message instanceof Node ? message : document.createTextNode(message));
    playlistStatus.classList.toggle('error', isError);
  };
  const readSession = key => {
    try { const value = sessionStorage.getItem(key); sessionStorage.removeItem(key); return value ? JSON.parse(value) : null; }
    catch { return null; }
  };
  const randomString = length => {
    const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
    return [...crypto.getRandomValues(new Uint8Array(length))].map(byte => alphabet[byte % alphabet.length]).join('');
  };
  const base64url = buffer => btoa(String.fromCharCode(...new Uint8Array(buffer))).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');

  const spotifyApi = async (path, options = {}) => {
    const url = path.startsWith('http') ? path : `https://api.spotify.com/v1${path}`;
    const response = await fetch(url, {
      ...options,
      headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json', ...(options.headers || {}) }
    });
    if (response.status === 429) {
      const wait = Number(response.headers.get('Retry-After') || 2);
      await new Promise(resolve => setTimeout(resolve, (wait + 1) * 1000));
      return spotifyApi(path, options);
    }
    if (response.status === 401) throw new Error('The Spotify session expired. Send again to sign in.');
    if (response.status === 403) {
      const detail = await response.json().catch(() => null);
      const reason = detail?.error?.message ? `${detail.error.message}. ` : '';
      throw new Error(`${reason}Spotify blocks this unless the app owner has Premium and every listener is added under Settings \u2192 User Management in the developer dashboard (five maximum while the app is in development mode).`);
    }
    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      throw new Error(detail?.error?.message || `Spotify refused the request (HTTP ${response.status}).`);
    }
    return response.status === 204 ? null : response.json();
  };

  const scopedRecords = () => playlistScope.value === 'bookmarks' ? records.filter(record => state.bookmarks.includes(record.key))
    : playlistScope.value === 'filtered' ? visibleRecords()
    : records;
  const playlistRecords = () => scopedRecords().filter(record => record.spotify_id);

  let playlistUrl = '';
  const linerNotes = () => {
    const chosen = scopedRecords();
    const lines = ['# __TITLE__', '', '__SUBTITLE__', ''];
    if (playlistUrl) lines.push(`Playlist: ${playlistUrl}`, '');
    lines.push(`${chosen.length} releases, in listening order.`, '');
    let era = '';
    chosen.forEach((record, index) => {
      if (record.section && record.section !== era) {
        era = record.section;
        lines.push(`## ${era}`, '');
      }
      const year = record.year ? ` (${record.year})` : '';
      const missing = record.spotify_id ? '' : ' — not on Spotify';
      lines.push(`### ${String(index + 1).padStart(2, '0')}. ${record.artist} — ${record.album}${year}${missing}`, '');
      if (record.note) lines.push(record.note, '');
      if (record.listen_for) lines.push(`*Listen for:* ${record.listen_for}`, '');
      lines.push(`Energy ${record.energy || '5'}/10 · ${record.texture || 'unclassified'}`, '');
    });
    lines.push('---', '', 'Notes from the Musiculum listening guide: __TITLE__.');
    return lines.join('\n');
  };

  const setLinerStatus = message => linerStatus.textContent = message;
  linerCopy.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(linerNotes());
      setLinerStatus(`Copied notes for ${scopedRecords().length} releases.`);
    } catch {
      setLinerStatus('This browser blocked the clipboard. Use the download instead.');
    }
  });
  linerDownload.addEventListener('click', () => {
    const blob = new Blob([linerNotes()], { type: 'text/markdown' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob); link.download = '__SLUG__-liner-notes.md'; link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    setLinerStatus(`Downloaded notes for ${scopedRecords().length} releases.`);
  });
  playlistScope.addEventListener('change', () => setLinerStatus(`Ready to share notes for ${scopedRecords().length} releases.`));
  setLinerStatus(`Ready to share notes for ${records.length} releases.`);

  const buildPlaylist = async () => {
    const chosen = playlistRecords();
    if (!chosen.length) { setPlaylistStatus('No releases match that selection.', true); return; }
    playlistSend.disabled = true;
    try {
      const wholeAlbums = playlistDepth.value === 'album';
      const uris = [];
      for (let index = 0; index < chosen.length; index += 20) {
        const batch = chosen.slice(index, index + 20);
        setPlaylistStatus(`Reading track lists… ${index + batch.length}/${chosen.length} releases.`);
        const data = await spotifyApi(`/albums?ids=${batch.map(record => record.spotify_id).join(',')}`);
        for (const album of data.albums || []) {
          if (!album) continue;
          const tracks = [...(album.tracks?.items || [])];
          let next = album.tracks?.next;
          while (wholeAlbums && next) {
            const page = await spotifyApi(next);
            tracks.push(...(page.items || []));
            next = page.next;
          }
          for (const track of wholeAlbums ? tracks : tracks.slice(0, 1)) if (track?.uri) uris.push(track.uri);
        }
      }
      if (!uris.length) throw new Error('Spotify returned no playable tracks for that selection.');
      setPlaylistStatus(`Creating a playlist of ${uris.length} tracks…`);
      const profile = await spotifyApi('/me');
      const playlist = await spotifyApi(`/users/${encodeURIComponent(profile.id)}/playlists`, {
        method: 'POST',
        body: JSON.stringify({
          name: playlistName.value.trim() || '__TITLE__',
          public: playlistPublic.checked,
          description: 'Built from the Musiculum listening guide: __TITLE__.'.slice(0, 300)
        })
      });
      for (let index = 0; index < uris.length; index += 100) {
        const slice = uris.slice(index, index + 100);
        await spotifyApi(`/playlists/${playlist.id}/tracks`, { method: 'POST', body: JSON.stringify({ uris: slice }) });
        setPlaylistStatus(`Adding tracks… ${index + slice.length}/${uris.length}.`);
      }
      const summary = document.createElement('span');
      summary.append(`Done. ${uris.length} tracks from ${chosen.length} releases. `);
      const link = document.createElement('a');
      playlistUrl = playlist.external_urls?.spotify || '';
      link.href = playlistUrl || 'https://open.spotify.com/collection/playlists';
      link.target = '_blank'; link.rel = 'noopener'; link.textContent = 'Open the playlist in Spotify';
      summary.append(link, ' Share the liner notes below alongside it.');
      setPlaylistStatus(summary);
      setLinerStatus('The notes now include a link to this playlist.');
    } catch (error) {
      setPlaylistStatus(error.message || 'Something went wrong talking to Spotify.', true);
    } finally {
      playlistSend.disabled = false;
    }
  };

  const beginAuth = async clientId => {
    const verifier = randomString(64);
    const oauthState = randomString(16);
    const challenge = base64url(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier)));
    sessionStorage.setItem(pkceKey, JSON.stringify({ verifier, state: oauthState, clientId, redirectUri }));
    sessionStorage.setItem(returnKey, location.href);
    sessionStorage.setItem(intentKey, JSON.stringify({
      name: playlistName.value, scope: playlistScope.value, depth: playlistDepth.value, isPublic: playlistPublic.checked
    }));
    const params = new URLSearchParams({
      client_id: clientId, response_type: 'code', redirect_uri: redirectUri,
      code_challenge_method: 'S256', code_challenge: challenge, state: oauthState,
      scope: 'playlist-modify-private playlist-modify-public'
    });
    location.assign(`https://accounts.spotify.com/authorize?${params}`);
  };

  const resumeAuth = async () => {
    const handoff = readSession(resultKey);
    const code = handoff?.code;
    const failure = handoff?.error;
    if (!code && !failure) return;
    const pending = readSession(pkceKey);
    const intent = readSession(intentKey);
    if (failure) { setPlaylistStatus(`Spotify sign-in did not complete (${failure}).`, true); return; }
    if (!pending || pending.state !== handoff.state) { setPlaylistStatus('That sign-in could not be verified. Try again.', true); return; }
    try {
      setPlaylistStatus('Finishing sign-in…');
      const response = await fetch('https://accounts.spotify.com/api/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          client_id: pending.clientId, grant_type: 'authorization_code', code,
          redirect_uri: pending.redirectUri, code_verifier: pending.verifier
        })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error_description || 'Spotify rejected the sign-in.');
      accessToken = data.access_token;
      if (!intent) { setPlaylistStatus('Connected to Spotify. Choose your options and send again.'); return; }
      playlistName.value = intent.name;
      playlistScope.value = intent.scope;
      playlistDepth.value = intent.depth;
      playlistPublic.checked = intent.isPublic;
      await buildPlaylist();
    } catch (error) {
      setPlaylistStatus(error.message || 'Could not complete the Spotify sign-in.', true);
    }
  };

  playlistSend.addEventListener('click', async () => {
    if (!configuredClientId) { setPlaylistStatus('Spotify Client ID is not configured for this guide yet. The site maintainer needs to finish the setup shown above.', true); return; }
    if (accessToken) { await buildPlaylist(); return; }
    setPlaylistStatus('Redirecting to Spotify to sign in…');
    await beginAuth(configuredClientId);
  });

  if (window.isSecureContext && window.crypto?.subtle) resumeAuth();
  else {
    playlistSend.disabled = true;
    setPlaylistStatus('Spotify sign-in needs a secure page. Serve this guide from http://127.0.0.1 or an https address and reload — it cannot run from a file:// URL.', true);
  }

  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) entry.target.classList.add('visible');
    }), { threshold: .08 });
    document.querySelectorAll('.reveal').forEach(element => observer.observe(element));
  }
  const timelineLinks = [...document.querySelectorAll('.timeline a')];
  const sectionObserver = new IntersectionObserver(entries => entries.forEach(entry => {
    if (entry.isIntersecting) timelineLinks.forEach(link => link.classList.toggle('active', link.hash === `#${entry.target.id}`));
  }), { rootMargin: '-35% 0px -55% 0px' });
  document.querySelectorAll('.story-section').forEach(section => sectionObserver.observe(section));
})();
