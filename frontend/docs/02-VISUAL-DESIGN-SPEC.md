# 02 — Visual Design Specification

> **Purpose:** Complete visual reference — wireframes, color system, typography, component specs, animation timing. Every pixel is accounted for. Build from this spec, don't improvise.
>
> **Audience:** Gen Z (16-26) — bold, fast, mobile-first, authentic
> **Visual Direction:** Cinematic Glassmorphism (dark + glass panels + burnt orange accent)

---

## 1. Design System

### 1.1 Color System

```
60% Primary:     #0A0A0F (deep black)     — page backgrounds, page-level
30% Secondary:   #14141F (near-black)     — cards, panels, glass surfaces
10% Accent:      #D4451A (burnt orange)   — CTAs, active states ONLY

Glass panel surface:
  background:  rgba(255, 255, 255, 0.04)
  border:      1px solid rgba(255, 255, 255, 0.08)
  backdrop-filter: blur(12px)

Text hierarchy:
  Primary:     #F0F0F5 (near-white)       — headings, body text
  Secondary:   #A0A0B0 (muted gray)       — metadata, labels, timestamps
  Disabled:    #505060 (dim gray)         — inactive, placeholder

Semantic colors:
  Error:       #E74C3C (red)              — generation failures, errors
  Success:     #2ECC71 (green)            — completed phases, ✅ checkmarks
  Warning:     #F39C12 (amber)            — ⚠️ quality issues, retries

Shapes:
  --radius:      8px   (standard cards)
  --radius-lg:   16px  (hero images, modal backgrounds)
  --radius-full: 9999px (pills, badges, selectors)
```

### ⚠️ Burnt Orange Usage Rule

`#D4451A` appears on EXACTLY these elements:
- Generate CTA button (filled bg)
- Active/selected state on filter pills
- Progress bar fill during generation
- Loading spinner during generation
- Active chapter in ChapterNav

`#D4451A` NEVER appears on:
- Headlines, titles, or body text
- Inactive/neutral states
- Card backgrounds
- Borders or dividers
- Decorative elements

**If orange is everywhere, nothing is memorable. Restraint is luxury.**

### 1.2 Typography

```css
/* Google Fonts import */
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@500;600;700&family=Inter:wght@300;400;500;600&display=swap');

:root {
  --font-display: 'Cinzel', serif;
  --font-body: 'Inter', sans-serif;

  /* Display scale (Cinzel) */
  --text-hero: 3.5rem;     /* 56px — landing hero title only */
  --text-display-xl: 2rem; /* 32px — page titles */
  --text-display-lg: 1.75rem; /* 28px — section titles */
  --text-display: 1.25rem; /* 20px — film titles in cards */

  /* Body scale (Inter) */
  --text-body: 1rem;       /* 16px — body, descriptions */
  --text-caption: 0.875rem; /* 14px — metadata, labels */
  --text-micro: 0.75rem;   /* 12px — timestamps, badges */

  /* Line heights */
  --leading-tight: 1.15;    /* Display text */
  --leading-normal: 1.4;    /* Small body */
  --leading-relaxed: 1.6;   /* Large body / story text */

  /* Font weights */
  --weight-light: 300;
  --weight-regular: 400;
  --weight-medium: 500;
  --weight-semibold: 600;
  --weight-bold: 700;

  /* Scale ratio: 1.25 (balanced — Gen Z reads fast, don't waste space) */
}
```

**Usage rules:**
- Cinzel for: Film titles, page headings ("Forge a Film"), hero text
- Inter for: EVERYTHING else — body, buttons, labels, badges, captions
- NEVER use Cinzel for body text, descriptions, or long-form reading
- NEVER use all-caps for more than 5 words

---

## 2. Page Wireframes

### 2.1 Landing Page (`/`)

```
┌──────────────────────────────────────────────────────────────────┐
│ [CHRONICLES]                                       [Forge][Library]│ ← Fixed top nav, glass panel
│                                                                    │     h-16, px-8, z-50
│ ┌────────────────────────────────────────────────────────────────┐ │
│ │  ▶  [HERO FILM BACKDROP — 16:9, rounded-2xl]                  │ │ ← aspect-video, bg-gradient
│ │       Auto-playing thumbnail of staff pick                     │ │     overlay glass bottom
│ │                                                               │ │
│ │       ╔═══════════════════════════════════════╗               │ │
│ │       ║     THE STAR FORGE                     ║               │ │ ← Cinzel 3.5rem, white
│ │       ║     Viking · 72s · 35 agents          ║               │ │ ← Inter 0.875rem, #A0A0B0
│ │       ╚═══════════════════════════════════════╝               │ │
│ │                                                               │ │
│ │       [▶ Watch Now]  [⚡ Create Your Own]                     │ │ ← Orange CTA, glass secondary
│ └────────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  TRENDING NOW                                                      │ ← Inter 1rem, #F0F0F5, semibold
│  ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ →                                │
│  │C1│ │C2│ │C3│ │C4│ │C5│ │C6│                                   │ ← FilmRow (horizontal scroll)
│  └──┘ └──┘ └──┘ └──┘ └──┘ └──┘                                   │     scroll-snap, peeking next card
│                                                                    │
│  ⚔️ VIKING SAGAS                                                   │
│  ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ →                                     │
│  │C1│ │C2│ │C3│ │C4│ │C5│                                        │
│  └──┘ └──┘ └──┘ └──┘ └──┘                                        │
│                                                                    │
│  🏛️ TALES OF POWER & CORRUPTION                                    │
│  ┌──┐ ┌──┐ ┌──┐ ┌──┐ →                                           │
│  │C1│ │C2│ │C3│ │C4│                                              │
│  └──┘ └──┘ └──┘ └──┘                                              │
│                                                                    │
│  🌍 ANCIENT WORLDS                                                 │
│  ┌──┐ ┌──┐ ┌──┐ ┌──┐ →                                           │
│  │C1│ │C2│ │C3│ │C4│                                              │
│  └──┘ └──┘ └──┘ └──┘                                              │
│                                                                    │
│  🔮 IDENTITY & TRUTH                                               │
│  ┌──┐ ┌──┐ ┌──┐ →                                                │
│  │C1│ │C2│ │C3│                                                    │
│  └──┘ └──┘ └──┘                                                    │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 Forge Page (`/forge`)

```
┌──────────────────────────────────────────────────────────────────┐
│ [CHRONICLES]                                       [Forge][Library]│
│                                                                    │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │                   ⚡ FORGE A FILM                             │ │ ← Cinzel 2rem, centered
│ │                                                                │ │
│ │  ┌─────────────────────────────────────────────────────────┐  │ │
│ │  │ What story do you want to tell?                         │  │ │ ← label, Inter 0.875rem, #A0A0B0
│ │  │ ┌─────────────────────────────────────────────────────┐ │  │ │
│ │  │ │ A blacksmith who forges a blade from fallen star... │ │  │ │ ← textarea
│ │  │ └─────────────────────────────────────────────────────┘ │  │ │     h-24, px-4, py-3
│ │  │                                           32 / 200      │  │ │     Inter 1rem
│ │  └─────────────────────────────────────────────────────────┘  │ │     char count: Inter 0.75rem
│ │                                                                │ │
│ │  ┌─ CULTURE ───────┐  ┌─ TIMELINE ──────┐  ┌─ THEME ─────┐  │ │
│ │  │ ▽ Viking        │  │ ▽ High Medieval │  │ ▽ Ambition  │  │ │ ← styled selects
│ │  │   Roman         │  │   Early Medieval│  │   Betrayal  │  │ │     glass bg, h-12
│ │  │   Egyptian      │  │   Age of Expl.. │  │   Loss       │  │ │     Inter 1rem
│ │  │   ...           │  │   ...            │  │   ...        │  │ │
│ │  └─────────────────┘  └─────────────────┘  └─────────────┘  │ │
│ │                                                                │ │
│ │  [⚡ Surprise Me]   Random film — one click                    │ │ ← orange outline, not filled
│ │                                                                │ │
│ │  ┌── ADVANCED ───────────────────────────────────────────┐   │ │ ← collapsible, hidden by default
│ │  │  Narration: [● ON]  Target: ~90 seconds               │   │ │
│ │  └───────────────────────────────────────────────────────┘   │ │
│ │                                                                │ │
│ │  ┌─────────────────────────────────────────────────────────┐  │ │
│ │  │               [⚡ FORGE FILM]                            │  │ │ ← BURNT ORANGE, full-width
│ │  └─────────────────────────────────────────────────────────┘  │ │     h-12, Cinzel 1.125rem
│ │                                                                │ │
│ │  ┌─ GENERATION PROGRESS ──────────────────────────────────┐  │ │ ← ONLY visible during gen
│ │  │  ████████████████████░░░░░░░░░░  67%                   │  │ │ ← orange fill, 300ms ease
│ │  │  Creating Visual Bible...                               │  │ │ ← current phase label
│ │  │                                                        │  │ │
│ │  │  ✅ Story  🔄 Visual Bible  ○ Images  ○ Video  ○ Post │  │ │ ← phase checklist
│ │  │     Lineage: ▸ Showrunner → Planner → Writer → ...     │  │ │ ← collapsible agent tree
│ │  └────────────────────────────────────────────────────────┘  │ │
│ └──────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### 2.3 Viewer Page (`/film/:hash`)

```
┌──────────────────────────────────────────────────────────────────┐
│ [← Back]            THE STAR FORGE                    [⛶ Cinema] │ ← sticky top bar, glass
│                                                                    │
│ ┌────────────────────────────────────────────────────────────────┐ │
│ │                                                                │ │
│ │            [16:9 VIDEO PLAYER — black background]              │ │ ← aspect-video, rounded-lg
│ │                                                                │ │     bg-black
│ │                                                                │ │
│ │            ▶  ⏮  ⏭  🔊 ─────●──────── 2:15 / 1:12           │ │ ← custom controls
│ └────────────────────────────────────────────────────────────────┘ │     glass overlay bottom
│                                                                    │
│  CHAPTERS                                                          │
│  [1. The River] [2. The Forge] [3. Confrontation] [4. The Test]  │ ← horizontal pills
│  [5. The Battle] [6. The Legacy]                                  │     active: orange bg
│                                                                    │     inactive: glass bg
│                                                                    │     scrollable on mobile
│  ┌─── CHARACTERS ────────┐  ┌─── STORY ───────────────────────┐  │
│  │ ┌────┐                 │  │                                  │  │
│  │ │┌──┐│ Bjorn           │  │ The river held its secret        │  │ ← story text syncs
│  │ ││IM││ Smith           │  │ beneath a sheet of ice that      │  │     with video playback
│  │ │└──┘│                 │  │ had not cracked in a thousand    │  │     Inter 0.875rem
│  │ └────┘                 │  │ winters. Bjorn knelt at the      │  │     #F0F0F5, leading-relaxed
│  │ ┌────┐                 │  │ frozen edge, his breath forming  │  │     max-h-64, overflow-y
│  │ │┌──┐│ Sigrid          │  │ ghosts in the predawn air...     │  │
│  │ ││IM││ Wife            │  │                                  │  │
│  │ │└──┘│                 │  │                                  │  │
│  │ └────┘                 │  │                                  │  │
│  └────────────────────────┘  └──────────────────────────────────┘  │
│                                                                    │
│  ▼ BEHIND THE SCENES                                               │ ← collapsible section
│     SHOWRUNNER                                                     │     Inter 0.875rem
│     ├─ PLANNER (3.2s, 450 tokens) ✅                              │     ✅ = completed
│     ├─ WRITER (4.1s, 680 tokens) ✅                                │     🔴 = failed
│     ├─ SCRIPT SUPERVISOR (2.8s, 320 tokens) ✅                     │     🔄 = in progress
│     ├─ DIRECTOR (5.2s, 890 tokens) ✅                              │
│     ├─ CHARACTER LEAD                                              │
│     │  ├─ Portrait Gen #1 (3.1s) ✅                                │
│     │  ├─ Portrait Gen #2 (2.9s) ✅                                │
│     │  └─ Portrait Gen #3 (3.3s) ✅                                │
│     ├─ VIDEO LEAD                                                  │
│     │  ├─ Scene 1 ✅  Scene 2 ✅  Scene 3 ✅                       │
│     │  ├─ Scene 4 ✅  Scene 5 ✅  Scene 6 ✅                       │
│     │  └─ Scene 7 ⚠️ (0.72 QC)  Scene 8 ✅  Scene 9 ✅           │
│     ├─ EDITOR (1.8s) ✅                                            │
│     ├─ SOUND DESIGNER (2.5s) ✅                                    │
│     └─ COLORIST (1.2s) ✅                                          │
│                                                                    │
│     Total: 35 agents · $0.00 · 2m 15s                              │
│                                                                    │
│  MORE LIKE THIS (Same culture)                                     │
│  ┌──┐ ┌──┐ ┌──┐ ┌──┐ →                                           │
│  │C1│ │C2│ │C3│ │C4│                                              │ ← FilmRow, same culture
│  └──┘ └──┘ └──┘ └──┘                                              │
└──────────────────────────────────────────────────────────────────┘
```

### 2.4 Library Page (`/library`)

```
┌──────────────────────────────────────────────────────────────────┐
│ [CHRONICLES]                                       [Forge][Library]│
│                                                                    │
│  ┌──────────────────────────────────────────┐                     │
│  │ 🔍  Search films by title, culture...    │                     │ ← search input, Inter
│  └──────────────────────────────────────────┘                     │     glass bg, h-12
│                                                                    │
│  [All Cultures ▾] [All Eras ▾] [All Themes ▾] [Newest ▾]         │ ← filter pills
│                                                                    │     glass bg, rounded-full
│                                                                    │     active: orange
│                                                                    │
│  ⚔️ VIKING SAGAS                               [See all →]        │
│  ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ →                                     │
│  │C1│ │C2│ │C3│ │C4│ │C5│                                        │
│  └──┘ └──┘ └──┘ └──┘ └──┘                                        │
│                                                                    │
│  🏛️ ROMAN EMPIRE                                [See all →]        │
│  ┌──┐ ┌──┐ ┌──┐ →                                                │
│  │C1│ │C2│ │C3│                                                    │
│  └──┘ └──┘ └──┘                                                    │
│                                                                    │
│  🌴 ANCIENT WORLDS                               [See all →]        │
│  ┌──┐ ┌──┐ ┌──┐ ┌──┐ →                                           │
│  │C1│ │C2│ │C3│ │C4│                                              │
│  └──┘ └──┘ └──┘ └──┘                                              │
│                                                                    │
│  (Rows continue for every culture/theme/timeline that has films)   │
│  (Empty cultures show a "Generate your first [culture] film!" CTA) │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Specifications

### 3.1 FilmCard

```
Props:
  film: FilmSummary
  onClick: () => void

Layout:
  Width: 240px (mobile), 280px (desktop)
  Glass card: bg rgba(255,255,255,0.04), border rgba(255,255,255,0.08)
  Rounded corners: --radius (8px)

Inside:
  ┌─────────────────────┐
  │ ┌─────────────────┐ │ ← 16:9 aspect ratio
  │ │   THUMBNAIL     │ │    object-fit: cover
  │ │    (16:9)      │ │    border-radius: 8px 8px 0 0
  │ └─────────────────┘ │
  │                     │
  │ The Star Forge      │ ← Inter 0.875rem, #F0F0F5, semibold
  │ Viking · 72s        │ ← Inter 0.75rem, #A0A0B0
  │                     │
  └─────────────────────┘

Interactive:
  Hover: transform: scale(1.05), transition: 200ms ease-out
  Focus: outline: 2px solid #D4451A
  Click: navigate to /film/{story_hash}

No hover video preview, no description text, no rating stars.
```

### 3.2 FilmRow

```
Props:
  title: string
  films: FilmSummary[]
  onFilmClick: (hash: string) => void

Layout:
  margin-bottom: 32px

Header:
  ┌────────────────────────────────────────────────────────────┐
  │  TITLE                                          [See all →]│ ← Inter 1rem, #F0F0F5, semibold
  └────────────────────────────────────────────────────────────┘

Scroll container:
  display: flex
  gap: 16px
  overflow-x: auto
  scroll-snap-type: x mandatory
  scroll-padding: 0 16px
  padding: 8px 0

Empty state:
  "No films yet. Be the first to create one!"
  "Create your first [culture/theme] film →" link

See all action:
  Only appears if more films exist than fit on screen
  Navigates to Library with filter pre-selected
```

### 3.3 ForgeForm

```
Components:
  SeedInput      — textarea, 10-200 chars, character counter
  CultureSelect  — styled <select>, grouped by category
  TimelineSelect — styled <select>, grouped by era bucket
  ThemeSelect    — styled <select>, grouped by theme category
  SurpriseMeBtn  — "⚡ Surprise Me" outline button
  ForgeBtn       — "⚡ Forge Film" filled orange CTA
  ProgressStream — progress bar + phase checklist + agent tree

Smart defaults:
  1. User selects a culture
  2. Timeline auto-selects that culture's natural era
  3. User can override timeline (this creates "counterfactual" mode)
  4. Theme is always manual (no default)

Validation:
  seed_idea: 10-200 chars (show error if <10 or >200)
  culture: required
  timeline: required
  theme: required

Surprise Me logic:
  Pick random culture + its natural era + random theme
  Show the roll: "🎲 Viking + High Medieval + Betrayal"
  User still clicks Forge to start generation
```

### 3.4 VideoPlayer

```
Props:
  videoUrl: string | null
  chapters: Chapter[]    // { id, title, timestamp, emoji }
  onChapterChange: (index: number) => void

Layout:
  width: 100%
  aspect-ratio: 16/9
  bg-black
  rounded-lg

Custom controls (glass overlay at bottom):
  ⏮  ⏯  ⏭    ─────●───────────    🔊 ━━●━━      ⛶
  |         |    |              |    |    |       |
  prev    play/pause   progress bar    volume    fullscreen
  
  Timeline: input[type=range], custom styled
  Volume: input[type=range], custom styled
  
  All controls auto-hide after 3s of no mouse movement
  Show on hover / touch

Chapters integration:
  Click chapter pill → seek to chapter timestamp
  Active chapter pill: orange bg
  Progress bar shows chapter markers as dots

Fullscreen (Cinema Mode):
  Native fullscreen API
  Controls still auto-hide
  ESC or click ⛶ to exit

Empty/loading state:
  Video not ready: centered loading spinner
  Failed: "Video generation failed" + retry button
  No URL: dark placeholder with "Film pending" message
```

### 3.5 AgentLineageTree

```
Props:
  events: SSEEvent[] (all events from the generation)

Layout:
  Collapsible section on ViewerPage
  Title: "▼ Behind the Scenes" (click to expand)

Tree structure:
  SHOWRUNNER                                         ← root level
  ├─ PLANNER (3.2s, 450 tokens) ✅                   ← agent with timing
  ├─ WRITER (4.1s, 680 tokens) ✅
  ├─ SCRIPT SUPERVISOR (2.8s) ✅
  ├─ DIRECTOR (5.2s, 890 tokens) ✅
  ├─ IMAGE SWARM LEAD                                 ← department head
  │  ├─ Portrait Gen #1 (3.1s) ✅                    ← worker
  │  ├─ Portrait Gen #2 (2.9s) ✅
  │  └─ Scene Keyframe #1 (3.3s) ✅
  ├─ VIDEO LEAD
  │  ├─ Scene 1 ✅  Scene 2 ✅  Scene 3 ✅
  │  └─ Scene 4 ⚠️ (0.72 QC pass)
  ├─ EDITOR (1.8s) ✅
  ├─ SOUND DESIGNER (2.5s) ✅
  └─ COLORIST (1.2s) ✅

Status icons:
  ✅ = completed (Success green)
  ⚠️ = completed with warning (Warning amber)
  🔴 = failed (Error red)
  🔄 = in progress (Accent orange, pulsing)

Summary footer:
  Total: N agents · $0.00 · Xm Xs

Mobile: flat list instead of tree, same data
```

---

## 4. Animation Spec

| Action | Duration | Easing | Notes |
|--------|----------|--------|-------|
| Film card hover | 200ms | ease-out | scale(1.05) |
| Film row scroll | 300ms | ease-out | CSS scroll-behavior |
| Page transition | 250ms | ease-out | fade in |
| Progress bar fill | 300ms | ease-in-out | width transition |
| Glass panel appear | 200ms | ease-out | opacity 0→1 |
| Hero auto-play | 3s | — | cycle through 3 films |
| Toast notification | 300ms in, 3s hold, 200ms out | ease-in-out | slide from top |
| Loading spinner | 800ms | linear | infinite rotation |
| Reduced motion | ALL = instant (0ms) | — | prefer-reduced-motion |

---

## 5. Responsive Breakpoints

| Breakpoint | Width | Layout Changes |
|-----------|-------|---------------|
| Mobile | < 640px | Single column, rows stack vertically, cards 160px wide |
| Tablet | 640-1024px | 2 rows, cards 200px |
| Desktop | > 1024px | Full Netflix layout, cards 280px |
| Cinema | fullscreen | Video fills screen, glass overlays |

Mobile-specific:
- Top nav collapses to hamburger menu
- Forge selectors stack vertically
- Viewer characters + story stack vertically (not side by side)
- Agent tree shows flat list (no indentation)
- Film rows scroll with momentum (CSS -webkit-overflow-scrolling: touch)

---

## 6. Empty States

| Page/Component | Empty State |
|----------------|-------------|
| Landing page | "No films yet. Generate your first film!" + Forge CTA |
| Library | "The vault is empty. Create your first epic." |
| FilmRow | "Nothing here yet. Create the first [culture/theme] film!" |
| FilmCard thumbnail | Colored placeholder with culture emoji + first letter of title |
| ChapterNav | "Scene generation in progress..." |
| VideoPlayer | Black screen with "Film pending..." or "Click Forge to start" |

---

## 7. What Makes This NOT a Generic AI Netflix Clone

| AI Default | What We Do | Why |
|------------|-----------|-----|
| Blue/purple accent | Burnt orange `#D4451A` | Warmer, cinematic, mimics fire/forge | 
| Glassmorphism everywhere | Glass only on overlays + cards | Functional (video behind text), not decorative |
| Rounded all corners | Sharp cards, round pills | Cards feel premium (Criterion, not SaaS) |
| Empty bento layouts | Content-driven horizontal scroll rows | Proven Netflix pattern, high content density |
| "Orchestrate your story" | "Forge a Film" | Active, visceral, fits forge/creation theme |
| 15-item dropdowns | Chunked groups of 3-7 | Miller's Law — chunking improves decision speed |
| Slow animations (800ms) | Fast animations (200-300ms) | Gen Z expects speed, not luxury |
| Purple ban ✅ | Orange rule | One memorable accent color, used sparingly |
