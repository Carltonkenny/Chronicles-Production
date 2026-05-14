# 🖥️ Phase 6: Frontend — Netflix-Style SPA (Week 13-14)

## Objective
Build a vanilla JavaScript SPA with cinematic Netflix-style UI: title card entry animations, chapter navigation, character galleries, story text sync, agent lineage view, and fullscreen cinema mode.

---

## Views

```
┌────────────────────────────────────────────────────────────────┐
│  VIEW 1: LANDING (/)                                          │
│                                                                │
│  Hero cinematic carousel with auto-playing film previews       │
│  "Chronicles Production" title with typewriter animation       │
│  "1,000 worlds. Infinite stories. One click." tagline          │
│  CTA button: "Create Your Film" → FORGE view                   │
│  Featured films grid (latest generated)                        │
│  Culture showcase cards (10 culture tiles)                     │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│  VIEW 2: FORGE (/forge)                                       │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Seed Idea                                               │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │ A blacksmith who forges a blade from fallen star... │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  │  10/200 characters                                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐           │
│  │   CULTURE    │ │   TIMELINE   │ │    THEME     │           │
│  │ ┌──────────┐ │ │ ┌──────────┐ │ │ ┌──────────┐ │           │
│  │ │ ████     │ │ │ │ ████     │ │ │ │ ████     │ │           │
│  │ │ ████     │ │ │ │ ████     │ │ │ │ ████     │ │           │
│  │ │ Viking ▲ │ │ │ │High Med ▲│ │ │ │Ambition ▲│ │           │
│  │ │ ████     │ │ │ │ ████     │ │ │ │ ████     │ │           │
│  │ └──────────┘ │ │ └──────────┘ │ │ └──────────┘ │           │
│  └──────────────┘ └──────────────┘ └──────────────┘           │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Narration: [ON] ●  Music: [ON] ●  Target: ~90 seconds  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              [ ⚡ GENERATE FILM ]                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  ┌─────────────────── PROGRESS (SSE) ──────────────────────┐  │
│  │ ████████████░░░░░░░░░░░░ Writing story... (33%)         │  │
│  │ ████████████████████████ Creating Visual Bible... (50%) │  │
│  │ ████████████████████████████████ Generating video...    │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│  VIEW 3: VIEWER (/film/{id}) — Netflix-Style                  │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                                                          │  │
│  │              ╔══════════════════════════╗                │  │
│  │              ║   THE STAR FORGE         ║                │  │
│  │              ║   A Viking Story         ║                │  │
│  │              ╚══════════════════════════╝                │  │
│  │              FADE IN (3 seconds)                         │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  ████████████████████████████████████████████████████    │  │
│  │  ████████████████████████████████████████████████████    │  │
│  │  █████████████████ VIDEO PLAYER █████████████████████    │  │
│  │  ████████████████████████████████████████████████████    │  │
│  │  ████████████████████████████████████████████████████    │  │
│  │                                                          │  │
│  │  ⏮  ▶  ⏭   ⏸   🔊  🔇  ⛶                              │  │
│  │  ─────●─────────────────────────────  1:12              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  CHAPTERS                                                │  │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐  │  │
│  │  │  1   │ │  2   │ │  3   │ │  4   │ │  5   │ │  6   │  │  │
│  │  │ 🧊   │ │ 🔥   │ │ 💔   │ │ ⚒️   │ │ ⚔️   │ │ 🌟   │  │  │
│  │  │ River│ │ Forge│ │Conf  │ │The   │ │Test  │ │Legacy│  │  │
│  │  │08:00 │ │08:00 │ │08:00 │ │08:00 │ │08:00 │ │08:00 │  │  │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  ┌──────────────────────────┐ ┌──────────────────────────────┐ │
│  │  CHARACTERS              │ │  STORY TEXT (sync-scrolls)    │ │
│  │  ┌───────────┐           │ │  The river held its secret    │ │
│  │  │   Bjorn   │           │ │  beneath a sheet of ice that  │ │
│  │  │  [IMAGE]  │           │ │  had not cracked in a         │ │
│  │  │  Smith    │           │ │  thousand winters. Bjorn      │ │
│  │  └───────────┘           │ │  knelt at the frozen edge,    │ │
│  │  ┌───────────┐           │ │  his breath forming ghosts    │ │
│  │  │   Sigrid  │           │ │  in the predawn air...        │ │
│  │  │  [IMAGE]  │           │ │                               │ │
│  │  │  Wife     │           │ │                               │ │
│  │  └───────────┘           │ │                               │ │
│  └──────────────────────────┘ └──────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  BEHIND THE SCENES                                       │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │ SHOWRUNNER                                          │  │  │
│  │  │  ├─ PLANNER (3200ms, 450 tokens)                    │  │  │
│  │  │  ├─ WRITER (4100ms, 680 tokens)                     │  │  │
│  │  │  ├─ SCRIPT SUPERVISOR (2800ms, 320 tokens)          │  │  │
│  │  │  ├─ DIRECTOR (5200ms, 890 tokens)                   │  │  │
│  │  │  ├─ CHARACTER LEAD                                    │  │  │
│  │  │  │   ├─ Portrait Gen #1 (3100ms) ✅                 │  │  │
│  │  │  │   ├─ Portrait Gen #2 (2900ms) ✅                 │  │  │
│  │  │  │   └─ Portrait Gen #3 (3300ms) ✅                 │  │  │
│  │  │  ├─ VIDEO LEAD                                        │  │  │
│  │  │  │   ├─ Scene 1 ✅  Scene 2 ✅  Scene 3 ✅          │  │  │
│  │  │  │   ├─ Scene 4 ✅  Scene 5 ✅  Scene 6 ✅          │  │  │
│  │  │  │   ├─ Scene 7 ⚠️(pass, 0.72)  Scene 8 ✅        │  │  │
│  │  │  │   └─ Scene 9 ✅                                    │  │  │
│  │  │  ├─ EDITOR (1800ms)                                   │  │  │
│  │  │  ├─ SOUND DESIGNER (2500ms)                           │  │  │
│  │  │  ├─ COLORIST (1200ms)                                 │  │  │
│  │  │  └─ QA SUPERVISOR (1900ms) ✅ ALL CLEAR               │  │  │
│  │  │                                                       │  │  │
│  │  │  Total: 35 agents · $0.00 budget · 2m 15s             │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│  VIEW 4: LIBRARY (/library)                                   │
│                                                                │
│  Search: [________________] 🔍                                │
│  Filter: [All Cultures ▼] [All Timelines ▼] [All Themes ▼]   │
│  Sort: [Newest ▼]                                             │
│                                                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │██████████│ │██████████│ │██████████│ │██████████│         │
│  │██████████│ │██████████│ │██████████│ │██████████│         │
│  │██████████│ │██████████│ │██████████│ │██████████│         │
│  │  THUMB   │ │  THUMB   │ │  THUMB   │ │  THUMB   │         │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘         │
│  Star Forge   River's End   Iron Crown   Desert Oath          │
│  Viking · 72s  Egypt · 68s  Roman · 81s  Mali · 75s           │
│  35 agents     32 agents     38 agents     34 agents          │
│  $0.00         $0.00         $0.00         $0.00              │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│  VIEW 5: PROFILE (/profile) — Optional (Auth-dependent)       │
│                                                                │
│  Tier: Free                                                    │
│  Generations today: 3/10                                       │
│  Total films: 42                                               │
│  Settings: narration default, music default, theme             │
└────────────────────────────────────────────────────────────────┘
```

---

## Technical Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Framework | **None** (Vanilla JS) | No build step, instant deploy, proven in MVP |
| Router | Custom hash-based SPA router | Simple, no framework dependency |
| State | Closure-based modules | Each view is self-contained |
| Video | HTML5 `<video>` element | Native, accessible, full-featured |
| API | `fetch()` + SSE `EventSource` | Native, no library needed |
| CSS | Modular (6 files) | layout.css → components.css → view-specific |
| Fonts | Inter (body) + Cinzel (titles) | Clean + cinematic |
| Theme | Glassmorphism dark | Black + transparent overlays + blur |
| Icons | Emoji (🧊🔥💔⚒️⚔️🌟) | Zero dependency, universal rendering |

---

## CSS Architecture

```css
/* layout.css — Grid, navigation, responsive containers */
/* components.css — Buttons, cards, inputs, selectors, progress bar */
/* landing.css — Hero carousel, culture showcase, featured films */
/* forge.css — Story creation form, selectors, preview */
/* viewer.css — Video player, chapter nav, character gallery, agent tree */
/* library.css — Film grid, search, filters */

:root {
  --bg-primary: #0A0A0F;
  --bg-secondary: #14141F;
  --bg-card: rgba(255, 255, 255, 0.05);
  --glass-border: rgba(255, 255, 255, 0.08);
  --glass-blur: 12px;
  --text-primary: #F0F0F5;
  --text-secondary: #A0A0B0;
  --accent: #D4451A;
  --accent-glow: rgba(212, 69, 26, 0.3);
  --success: #2ECC71;
  --warning: #F39C12;
  --error: #E74C3C;
  --font-body: 'Inter', sans-serif;
  --font-cinematic: 'Cinzel', serif;
  --radius: 8px;
  --radius-lg: 16px;
  --transition: 200ms ease;
}
```

---

## JavaScript Module Structure

```
js/
├── core/
│   ├── app.js          # SPA router, view mounting, navigation
│   └── auth.js         # Auth state (localStorage-based, optional Supabase)
├── api/
│   └── api.js          # fetch() + SSE EventSource wrapper
├── pages/
│   ├── landing.js      # Hero carousel, featured films
│   ├── forge.js        # Film creation form, SSE progress
│   ├── viewer.js       # Video player, chapters, characters, agent tree
│   ├── library.js      # Film grid, search, filters
│   └── profile.js      # User settings (optional)
└── components/
    ├── hero-carousel.js # Auto-rotating film showcase
    ├── chapter-selector.js # Click-to-jump scene navigation
    ├── character-gallery.js # Character portraits + bios modal
    ├── video-player.js  # HTML5 video with custom controls
    ├── agent-lineage.js # Collapsible tree view
    └── ui.js           # Toast, modal, tooltip, loading spinner
```

---

## SPA Router

```javascript
// js/core/app.js
class ChroniclesRouter {
  constructor() {
    this.routes = {
      '/': LandingView,
      '/forge': ForgeView,
      '/film/:id': Viewer,
      '/library': LibraryView,
      '/profile': ProfileView
    };
    window.addEventListener('hashchange', () => this.navigate());
  }
  
  navigate() {
    const hash = window.location.hash.slice(1) || '/';
    const [path, id] = hash.split('/film/').length > 1 
      ? ['/film/:id', hash.split('/film/')[1]]
      : [hash, null];
    
    // Mount the matching view
    const View = this.routes[path];
    if (View) {
      const view = new View(id);
      document.getElementById('app').innerHTML = '';
      document.getElementById('app').appendChild(view.render());
    }
  }
}
```

---

## SSE Progress Streaming

```javascript
// js/pages/forge.js
function startGeneration(request) {
  const eventSource = new EventSource(
    `/api/v4/generate-film/stream?seed_idea=${encodeURIComponent(request.seed_idea)}&culture=${request.culture}&timeline=${request.timeline}&theme=${request.theme}`
  );
  
  eventSource.addEventListener('progress', (e) => {
    const data = JSON.parse(e.data);
    updateProgressBar(data.phase, data.percent);
    
    switch (data.phase) {
      case 'story':
        showStatus('Writing story...');
        break;
      case 'visual_bible':
        showStatus('Creating Visual Bible...');
        break;
      case 'images':
        showStatus(`Generating ${data.total} images...`);
        break;
      case 'videos':
        showStatus(`Rendering scene ${data.scene_index}/${data.scene_total}...`);
        break;
      case 'post':
        showStatus('Assembling final film...');
        break;
    }
  });
  
  eventSource.addEventListener('done', (e) => {
    const film = JSON.parse(e.data);
    eventSource.close();
    window.location.hash = `#/film/${film.film_id}`;
  });
  
  eventSource.addEventListener('error', (e) => {
    showError('Generation failed. Please try again.');
    eventSource.close();
  });
}
```

---

## Tasks

| # | Task | Effort | Depends On |
|---|------|--------|-----------|
| 6.1 | Create HTML shell + CSS theme variables | 2h | — |
| 6.2 | Implement SPA router (hash-based) | 2h | 6.1 |
| 6.3 | Build Landing view (hero carousel) | 4h | 6.2 |
| 6.4 | Build Forge view (creation form + SSE) | 6h | 6.2 |
| 6.5 | Build Viewer (video player + chapters) | 8h | 6.2 |
| 6.6 | Build character gallery component | 3h | 6.5 |
| 6.7 | Build agent lineage tree component | 3h | 6.5 |
| 6.8 | Build story text sync-scroll component | 2h | 6.5 |
| 6.9 | Build Library view (grid + search) | 4h | 6.2 |
| 6.10 | Build Profile view (optional) | 2h | 6.2 |
| 6.11 | Add title card entry animation (CSS) | 2h | 6.5 |
| 6.12 | Add fullscreen cinema mode | 2h | 6.5 |
| 6.13 | CSS glassmorphism polish (all views) | 4h | 6.3-6.12 |
| 6.14 | Responsive design (mobile + desktop) | 4h | 6.3-6.12 |
| 6.15 | Write frontend integration test | 2h | 6.14 |

**Total: ~50 hours (Week 13-14)**

---

## Verification Checklist
- [ ] All 5 views navigate without page reload
- [ ] Landing hero carousel auto-rotates
- [ ] Forge form submits + SSE progress streams
- [ ] Viewer plays film with chapter navigation
- [ ] Chapter selector jumps to correct scene timestamp
- [ ] Character gallery shows all character portraits
- [ ] Story text scrolls in sync with video playback
- [ ] Agent lineage tree expands/collapses
- [ ] Fullscreen cinema mode works
- [ ] Library search + filter + sort works
- [ ] Mobile responsive: all views usable on 375px width
- [ ] Glassmorphism theme consistent across all views