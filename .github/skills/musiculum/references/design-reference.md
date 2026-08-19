# HTML Report Design Reference

This file contains the complete CSS and JS template that `fetch_spotify.py` should use when generating `index.html`.

## Full CSS

```css
/* ── Reset & Base ─────────────────────────────────────────── */
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth;font-size:17px}
body{
  font-family:'Georgia','Times New Roman',serif;
  background:#0a0a0c;
  color:#d4cfc6;
  line-height:1.75;
  overflow-x:hidden;
}
::selection{background:#c0392b;color:#fff}

/* ── Scrollbar ────────────────────────────────────────────── */
::-webkit-scrollbar{width:6px}
::-webkit-scrollbar-track{background:#111}
::-webkit-scrollbar-thumb{background:#3a2020;border-radius:3px}

/* ── Typography ───────────────────────────────────────────── */
h1,h2,h3{font-family:'Helvetica Neue','Arial',sans-serif;font-weight:700;letter-spacing:-.02em}
h1{font-size:clamp(2.4rem,6vw,4.2rem);line-height:1.1;color:#f0ebe3}
h2{font-size:clamp(1.6rem,4vw,2.6rem);line-height:1.2;color:#e8c8a0;margin-bottom:1rem}
h3{font-size:.85rem;color:#c9a96e;margin-bottom:.5rem;text-transform:uppercase;letter-spacing:.08em}
p{margin-bottom:1.3rem;max-width:68ch}
strong{color:#e8c8a0}
em{color:#bfab8a;font-style:italic}
a{color:#c0785a;text-decoration:none;border-bottom:1px solid rgba(192,120,90,.3);transition:border-color .3s}
a:hover{border-color:#c0785a}

/* ── Layout ───────────────────────────────────────────────── */
.page-wrapper{display:flex;min-height:100vh}

/* ── Sidebar Timeline ─────────────────────────────────────── */
.sidebar{
  position:fixed;top:0;left:0;width:220px;height:100vh;
  background:linear-gradient(180deg,#0d0d10,#12111a);
  border-right:1px solid #1e1b28;
  padding:2rem 1rem;display:flex;flex-direction:column;justify-content:center;
  z-index:100;overflow-y:auto;
}
.sidebar-title{font-family:'Helvetica Neue','Arial',sans-serif;font-size:.65rem;text-transform:uppercase;letter-spacing:.2em;color:#5a5262;margin-bottom:1.5rem;padding-left:.5rem}
.timeline{list-style:none;position:relative;padding-left:1.2rem}
.timeline::before{content:'';position:absolute;left:0;top:0;bottom:0;width:2px;background:#1e1b28}
.timeline li{position:relative;margin-bottom:1.2rem}
.timeline li::before{content:'';position:absolute;left:-1.2rem;top:.45rem;width:8px;height:8px;border-radius:50%;background:#2a2535;border:2px solid #3a3345;transition:all .4s ease}
.timeline li.active::before{background:#c0785a;border-color:#e8a87c;box-shadow:0 0 12px rgba(192,120,90,.5)}
.timeline a{font-family:'Helvetica Neue','Arial',sans-serif;font-size:.75rem;color:#5a5262;text-decoration:none;border:none;display:block;padding:.15rem 0;transition:color .3s;line-height:1.3}
.timeline li.active a{color:#e8c8a0}
.timeline a:hover{color:#c0785a}
.timeline .era-year{display:block;font-size:.6rem;color:#3a3345;margin-top:.1rem;font-family:monospace}
.timeline li.active .era-year{color:#7a6858}

/* ── Main Content ─────────────────────────────────────────── */
.main-content{margin-left:220px;flex:1;min-height:100vh}

/* ── Hero ──────────────────────────────────────────────────── */
.hero{min-height:100vh;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;padding:4rem 2rem;background:radial-gradient(ellipse at 50% 80%,rgba(100,30,20,.15) 0%,transparent 60%),radial-gradient(ellipse at 20% 20%,rgba(40,20,60,.2) 0%,transparent 50%),#0a0a0c;position:relative}
.hero::after{content:'';position:absolute;bottom:0;left:0;right:0;height:120px;background:linear-gradient(transparent,#0a0a0c)}
.hero .subtitle{font-size:clamp(.95rem,2vw,1.15rem);color:#7a7268;max-width:55ch;line-height:1.6;font-style:italic}
.hero .scroll-hint{margin-top:3rem;font-size:.7rem;text-transform:uppercase;letter-spacing:.25em;color:#3a3535;animation:pulse-down 2s infinite}
@keyframes pulse-down{0%,100%{opacity:.3;transform:translateY(0)}50%{opacity:.8;transform:translateY(6px)}}

/* ── Section ──────────────────────────────────────────────── */
.section{padding:6rem 3rem 4rem;max-width:900px;margin:0 auto;position:relative}
.section::before{content:'';position:absolute;top:0;left:50%;transform:translateX(-50%);width:60px;height:1px;background:linear-gradient(90deg,transparent,#3a2020,transparent)}
.section-number{font-family:monospace;font-size:.7rem;color:#3a2020;letter-spacing:.15em;text-transform:uppercase;margin-bottom:.5rem;display:block}

/* ── Album Cards Grid ─────────────────────────────────────── */
.album-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1.2rem;margin:2.5rem 0 3rem}
.album-card{background:linear-gradient(135deg,#13121a,#0f0e15);border:1px solid #1e1b28;border-radius:8px;padding:1.2rem;transition:transform .4s ease,border-color .4s ease,box-shadow .4s ease;position:relative;overflow:hidden}
.album-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,#c0785a,transparent);opacity:0;transition:opacity .4s}
.album-card:hover{transform:translateY(-4px);border-color:#2a2535;box-shadow:0 8px 32px rgba(0,0,0,.4)}
.album-card:hover::before{opacity:1}
.album-card .card-artist{font-family:'Helvetica Neue','Arial',sans-serif;font-size:.7rem;text-transform:uppercase;letter-spacing:.12em;color:#7a6858;margin-bottom:.2rem}
.album-card .card-album{font-size:1.05rem;color:#e8c8a0;font-weight:600;margin-bottom:.15rem;font-family:'Helvetica Neue','Arial',sans-serif}
.album-card .card-year{font-family:monospace;font-size:.7rem;color:#3a3345;margin-bottom:.6rem}
.album-card .card-note{font-size:.82rem;color:#8a8278;line-height:1.5;margin-bottom:.8rem}
.album-card .spotify-embed{border-radius:6px;overflow:hidden;margin-top:.5rem}
.album-card .spotify-embed iframe{border:0;width:100%;border-radius:6px}

/* ── Featured Album ───────────────────────────────────────── */
.featured-album{margin:2rem 0 2.5rem;padding:1.5rem;background:linear-gradient(135deg,rgba(100,30,20,.08),rgba(20,18,30,.4));border:1px solid #2a1f2f;border-radius:10px}
.featured-album .feat-label{font-family:'Helvetica Neue','Arial',sans-serif;font-size:.6rem;text-transform:uppercase;letter-spacing:.2em;color:#5a4a3a;margin-bottom:.8rem}
.featured-album iframe{border:0;width:100%;border-radius:8px}

/* ── Era Dividers ─────────────────────────────────────────── */
.era-divider{height:40vh;display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden}
.era-divider .era-bg{position:absolute;inset:0;background-size:cover;background-position:center;filter:brightness(.2) saturate(.4);transform:scale(1.1);transition:transform 1s ease}
.era-divider:hover .era-bg{transform:scale(1.15)}
.era-divider .era-label{position:relative;z-index:1;font-family:'Helvetica Neue','Arial',sans-serif;font-size:clamp(1.2rem,3vw,2rem);font-weight:700;color:#f0ebe3;text-transform:uppercase;letter-spacing:.15em;text-shadow:0 2px 20px rgba(0,0,0,.8)}
.era-divider .era-years{position:relative;z-index:1;font-family:monospace;font-size:.75rem;color:#7a6858;margin-top:.5rem;letter-spacing:.2em}

/* ── Scroll Reveal ────────────────────────────────────────── */
.reveal{opacity:0;transform:translateY(40px);transition:opacity .8s ease,transform .8s ease}
.reveal.from-left{transform:translateX(-40px)}
.reveal.from-right{transform:translateX(40px)}
.reveal.scale-in{transform:scale(.92);transform-origin:center}
.reveal.visible{opacity:1;transform:translateY(0) translateX(0) scale(1)}
.stagger .album-card{opacity:0;transform:translateY(30px);transition:opacity .6s ease,transform .6s ease}
.stagger.visible .album-card{opacity:1;transform:translateY(0)}
.stagger.visible .album-card:nth-child(1){transition-delay:.05s}
.stagger.visible .album-card:nth-child(2){transition-delay:.1s}
.stagger.visible .album-card:nth-child(3){transition-delay:.15s}
.stagger.visible .album-card:nth-child(4){transition-delay:.2s}
.stagger.visible .album-card:nth-child(5){transition-delay:.25s}
.stagger.visible .album-card:nth-child(6){transition-delay:.3s}
.stagger.visible .album-card:nth-child(7){transition-delay:.35s}
.stagger.visible .album-card:nth-child(8){transition-delay:.4s}
.stagger.visible .album-card:nth-child(9){transition-delay:.45s}
.stagger.visible .album-card:nth-child(10){transition-delay:.5s}
.stagger.visible .album-card:nth-child(n+11){transition-delay:.55s}

/* ── Responsive ───────────────────────────────────────────── */
@media(max-width:768px){.sidebar{display:none}.main-content{margin-left:0}.section{padding:4rem 1.5rem 3rem}.album-grid{grid-template-columns:1fr}}
@media(min-width:769px) and (max-width:1024px){.sidebar{width:180px}.main-content{margin-left:180px}}
```

## JavaScript

```js
(function(){
  // ── Scroll Reveal ──
  const reveals = document.querySelectorAll('.reveal');
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) entry.target.classList.add('visible');
    });
  }, { threshold: 0.08, rootMargin: '0px 0px -60px 0px' });
  reveals.forEach(el => observer.observe(el));

  // ── Sidebar Active Section ──
  const sections = document.querySelectorAll('[id^="hero"],[id^="section-"]');
  const timelineItems = document.querySelectorAll('.timeline li');
  const sectionMap = {};
  timelineItems.forEach(li => { sectionMap[li.dataset.section] = li; });

  const sectionObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        timelineItems.forEach(li => li.classList.remove('active'));
        if (sectionMap[entry.target.id]) sectionMap[entry.target.id].classList.add('active');
      }
    });
  }, { threshold: 0.15, rootMargin: '-20% 0px -60% 0px' });
  sections.forEach(s => sectionObserver.observe(s));

  // ── Smooth scroll for timeline links ──
  document.querySelectorAll('.timeline a').forEach(a => {
    a.addEventListener('click', (e) => {
      e.preventDefault();
      const target = document.querySelector(a.getAttribute('href'));
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });

  // ── Parallax-lite on era dividers ──
  const dividers = document.querySelectorAll('.era-divider .era-bg');
  if (dividers.length && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    let ticking = false;
    window.addEventListener('scroll', () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          dividers.forEach(bg => {
            const rect = bg.parentElement.getBoundingClientRect();
            const offset = (rect.top + rect.height / 2 - window.innerHeight / 2) * 0.12;
            bg.style.transform = `scale(1.1) translateY(${offset}px)`;
          });
          ticking = false;
        });
        ticking = true;
      }
    });
  }
})();
```

## HTML Structure Pattern

For each `## Section` in the markdown essay, generate:

```html
<!-- Era Divider -->
<div class="era-divider">
  <div class="era-bg" style="background:linear-gradient(135deg,#1a0a0a,#0a0a15)"></div>
  <div style="text-align:center">
    <div class="era-label reveal">Section Title</div>
    <div class="era-years reveal" style="transition-delay:.2s">Year Range</div>
  </div>
</div>

<!-- Section Content -->
<section class="section" id="section-N">
  <span class="section-number reveal">Section 0N</span>
  <h2 class="reveal">Section Title</h2>

  <!-- Narrative paragraphs, each wrapped in <div class="reveal"> -->
  <div class="reveal"><p>Essay text...</p></div>

  <!-- Featured album (first/most important album of the section) -->
  <div class="featured-album reveal scale-in">
    <div class="feat-label">Label Text</div>
    <iframe src="https://open.spotify.com/embed/album/ALBUM_ID?utm_source=generator&theme=0"
            height="352" allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
            loading="lazy"></iframe>
  </div>

  <!-- Album cards grid -->
  <h3 class="reveal">Recommended Listening</h3>
  <div class="album-grid stagger reveal">
    <div class="album-card">
      <div class="card-artist">ARTIST</div>
      <div class="card-album">ALBUM</div>
      <div class="card-year">YEAR</div>
      <div class="card-note">NOTE</div>
      <div class="spotify-embed">
        <iframe src="https://open.spotify.com/embed/album/ALBUM_ID?utm_source=generator&theme=0"
                height="152" allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
                loading="lazy"></iframe>
      </div>
    </div>
    <!-- ... more cards -->
  </div>
</section>
```

## Sidebar Structure

```html
<nav class="sidebar">
  <div class="sidebar-title">Genre Timeline</div>
  <ul class="timeline">
    <li data-section="hero"><a href="#hero">Introduction<span class="era-year">Overview</span></a></li>
    <li data-section="section-1"><a href="#section-1">Section Name<span class="era-year">Year Range</span></a></li>
    <!-- ... one li per section -->
  </ul>
</nav>
```
