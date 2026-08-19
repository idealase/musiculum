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
    if (target) selectRecord(target.dataset.key);
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
    (!textureFilter.value || (record.texture || 'unclassified') === textureFilter.value) &&
    Number(record.energy || 5) >= Number(energyFilter.value)
  );
  const updateFilters = () => {
    const visible = new Set(visibleRecords().map(record => record.key));
    document.querySelectorAll('.album-card,.map-point,.graph-node').forEach(element => {
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
