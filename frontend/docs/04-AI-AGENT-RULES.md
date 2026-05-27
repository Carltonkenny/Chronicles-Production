# 04 — AI Agent Rules: Frontend Coding Contract

> **Purpose:** These rules prevent AI-generated React bugs. Copy this into CLAUDE.md before any AI agent writes frontend code. Every rule is derived from an actual bug found in the backend (see `00-BUG-PREVENTION-CONTRACT.md`).
>
> **Status:** Mandatory. Read before coding. Violations are automatically rejected.

---

## R1: SSE Events Use Named Types (BLOCKER)

```typescript
// ✅ CORRECT — listen to named events
es.addEventListener('story', handler)
es.addEventListener('visual_bible', handler)
es.addEventListener('images', handler)
es.addEventListener('done', handler)

// ❌ WRONG — onmessage catches ALL events, can't discriminate
es.onmessage = (e) => { ... }
```

**Why:** The backend sends `event: story`, `event: visual_bible`, etc. If you use `onmessage`, all events arrive at one handler with no way to tell them apart. You'd need to manually parse `event.type` which `addEventListener` already does for you.

---

## R2: One Done Event (BLOCKER)

```typescript
es.addEventListener('done', (e) => {
  const data = JSON.parse(e.data)
  // ✅ CORRECT: only respond to pct === 100
  if (data.pct === 100) {
    navigate(`/film/${hash}`)
  }
})
```

**Why:** The backend currently emits two `done` events. The first one fires at 85% with story+image data (before video generation). The second fires at 100% with the complete film. Only navigate on pct=100. This will be fixed in the backend (done → pipeline_complete), but defensive code matters until then.

---

## R3: SSE Data Shapes Are Per-Phase (BLOCKER)

```typescript
// ✅ CORRECT — access data ONLY when you know the phase has it
// story phase → data is empty, never read it
// visual_bible complete → data has the bible
// images complete → data has scenes + characters
// done → data has mp4_url + audio_url

// ❌ WRONG — assuming data always has the same shape
const scenes = event.data?.scenes  // crashes on story events
```

**Why:** The `data` field changes shape 6 times across the SSE stream. `story` events have `data: {}`. `images` events have `data: {scenes, characters}`. If you treat them all the same, you'll access undefined fields and crash.

---

## R4: One Zustand Store (BLOCKER)

```typescript
// ✅ CORRECT — one store for all film state
const useFilmStore = create<FilmState>((set) => ({ ... }))

// ❌ WRONG — multiple stores, contexts, or local state for global data
const useCatalogStore = ...  // NO
const AppContext = ...       // NO
const [films, set] = useState()  // NO for catalog
```

**Why:** Zustand is 1KB. One store means one source of truth. Multiple stores create synchronization bugs where one store thinks the generation is running while another thinks it's idle. You can't have that race condition with one store.

---

## R5: Events Are Append-Only (BLOCKER)

```typescript
// ✅ CORRECT — append new events to the array
addEvent: (event) => set((state) => ({ events: [...state.events, event] }))

// ❌ WRONG — overwrite
set({ events: [event] })
```

**Why:** The progress bar needs to know the LATEST event's pct. The phase checklist needs to see ALL events to know which phases are complete. Both read from the same array. If you overwrite, you lose history.

---

## R6: Accumulate Phase Data Separately (BLOCKER)

```typescript
// ✅ CORRECT — each phase has its own field in the store
visualBibleData: null
imagesData: null
videoData: null
doneData: null

// ❌ WRONG — merge everything into one object
mergedData: {}  // visual bible overwrites images
```

**Why:** Visual bible, images, and video data have different shapes and are used by different UI components. If you merge them into one object, the VideoPlayer tries to render visual bible data and crashes.

---

## R7: No useEffect for SSE Lifecycle (BLOCKER)

```typescript
// ✅ CORRECT — custom hook manages EventSource
function useGeneration(onComplete) {
  const esRef = useRef(null)
  
  const start = (req) => {
    esRef.current?.close()
    esRef.current = new EventSource(...)
  }
  
  useEffect(() => {
    return () => esRef.current?.close()  // cleanup on unmount
  }, [])
  
  return { start, cancel: () => esRef.current?.close() }
}

// ❌ WRONG — creating EventSource inside useEffect
useEffect(() => {
  const es = new EventSource(...)  // useEffect runs twice in dev mode
  return () => es.close()           // creates and destroys on every render
}, [])
```

**Why:** React 19 Strict Mode double-invokes effects in development. If you create EventSource inside `useEffect`, you get two connections. The custom hook pattern avoids this by keeping the EventSource ref stable and only creating it when the user explicitly clicks "Generate."

---

## R8: Loading States Are Quad-State (MANDATORY)

```typescript
// Every async operation has 4 states:
type AsyncState<T> = 
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: string }

// ✅ CORRECT — render each state
function Catalog() {
  const { catalogLoading, catalogError, films } = useFilmStore()
  
  if (catalogLoading) return <LoadingSkeleton />
  if (catalogError) return <ErrorState message={catalogError} />
  if (films.length === 0) return <EmptyState />
  return <FilmList films={films} />
}

// ❌ WRONG — render without checking
return <FilmList films={films} />  // undefined crash if not loaded
```

---

## R9: FilmCard Spec Is Exact (MANDATORY)

```typescript
// FilmCard shows EXACTLY these three things:
function FilmCard({ film }: { film: FilmSummary }) {
  return (
    <div className="w-[240px] md:w-[280px] rounded-lg glass-card">
      {/* 1. 16:9 thumbnail */}
      <div className="aspect-video overflow-hidden rounded-t-lg">
        <img src={film.thumbnail_url} alt={film.title}
          className="w-full h-full object-cover hover:scale-105 transition-transform duration-200"
        />
      </div>
      {/* 2. Title */}
      <p className="text-[#F0F0F5] font-inter text-sm font-semibold px-3 pt-2">
        {film.title}
      </p>
      {/* 3. Culture · Duration */}
      <p className="text-[#A0A0B0] font-inter text-xs px-3 pb-3">
        {film.culture_display} · {film.duration}s
      </p>
    </div>
  )
}
```

**NO hover video preview** (requires loading video clips — too expensive)
**NO description text** (too long for cards)
**NO ratings** (we don't have that data)

---

## R10: Burnt Orange Is Rare (MANDATORY)

```typescript
// Color: #D4451A
// Appears ONLY on:
// 1. Generate CTA button (filled bg)
// 2. Active filter/chapter pills
// 3. Progress bar fill
// 4. Loading spinner

// Colors that are NOT burnt orange:
// - Page backgrounds: #0A0A0F
// - Text: #F0F0F5 (headings) and #A0A0B0 (metadata)
// - Card backgrounds: rgba(255,255,255,0.04)
// - Error: #E74C3C
// - Success: #2ECC71
```

---

## R11: Typography Is Specified (MANDATORY)

```css
/* Font usage: */
Cinzel (serif) → Film titles, page headings only
Inter (sans-serif) → EVERYTHING else: body text, buttons, labels, cards, pills

/* NEVER use Cinzel for: */
- Body text or paragraphs
- Button labels
- Form labels
- Badges or metadata
- Navigation links

/* NEVER use Inter for: */
- Hero film title (Cinzel only)
- Page-level headings (Cinzel only)
```

---

## R12: Hash Calculation (MANDATORY)

```typescript
function computeStoryHash(culture: string, timeline: string, theme: string, seed: string): string {
  // SHA-256 of pipe-separated inputs
  // This matches /generate-film (not /generate-story)
  const input = `${culture}|${timeline}|${theme}|${seed}`
  // ... SHA-256, first 16 chars
}
```

**Why:** `/generate-story` hashes the LLM output (different every time). `/generate-film` hashes the input (deterministic). Use the input-based hash for cache lookups and consistent film IDs.

---

## R13: Audio URL May Be Null (MANDATORY)

```typescript
// The done event may have audio_url: null
// The /api/audio/{hash} endpoint may return 404
// ALWAYS guard audio playback:
if (doneData.audio_url) {
  <audio src={doneData.audio_url} />
} else {
  <p>No narration available</p>
}
```

---

## R14: Error Boundaries Per Page (MANDATORY)

```typescript
// Each page wrapped in its own ErrorBoundary
function App() {
  return (
    <Routes>
      <Route path="/" element={<ErrorBoundary><LandingPage /></ErrorBoundary>} />
      <Route path="/forge" element={<ErrorBoundary><ForgePage /></ErrorBoundary>} />
      <Route path="/film/:hash" element={<ErrorBoundary><ViewerPage /></ErrorBoundary>} />
      <Route path="/library" element={<ErrorBoundary><LibraryPage /></ErrorBoundary>} />
    </Routes>
  )
}
```

---

## R15: No Libraries Beyond the Stack (STRICT)

Approved:
- React 19, React Router v7, Zustand, Tailwind CSS v4
- Native `fetch`, native `EventSource`

Rejected:
- Axios, React Query, SWR, Redux, Jotai, Recoil
- Material UI, Ant Design, shadcn/ui, Headless UI
- Framer Motion (use CSS transitions)
- date-fns, lodash (format manually)
- Any carousel/slider library (use CSS scroll-snap)

**Every additional library is a vector for AI-style bugs.** The CSS scroll-snap pattern for FilmRow replaces 3 libraries (carousel + slider + scroll behavior) with 4 CSS properties.

---

## R16: The "No Derived State in useEffect" Rule (MANDATORY)

```typescript
// ✅ CORRECT — computed value, not state
const latestPct = events.length > 0 ? events[events.length - 1].pct : 0

// ❌ WRONG — derived state in useEffect
const [pct, setPct] = useState(0)
useEffect(() => {
  if (events.length > 0) setPct(events[events.length - 1].pct)
}, [events])
```

**Why:** Derived state causes unnecessary re-renders and can become stale. If `events` updates twice in one frame, the second `setPct` is batched away. Reading from `events` directly is always current.

---

## R17: Responsive Before Desktop (MANDATORY)

```typescript
// Design for mobile FIRST (375px), extend to desktop
// Use Tailwind's sm/md/lg prefixes
// Don't start with desktop and add "mobile below"

// ✅ CORRECT
<div className="flex-col md:flex-row gap-4">
  <div className="w-full md:w-[240px]">...</div>
  <!-- Mobile: full-width stack, Desktop: side by side -->
</div>
```

---

## R18: Commit Messages Follow the Project Convention (MANDATORY)

When committing frontend code:
```
feat(frontend): add LandingPage with hero carousel and film rows
fix(frontend): handle null audio_url in ViewerPage
docs(frontend): update API contract with new catalog endpoints
```

No "wip", "fixes", "update", or AI-generated commit messages.

---

## Rule Enforcement

These 18 rules are checked on every PR/review:

| Rule | Type | Check |
|------|------|-------|
| R1-R3 | BLOCKER | SSE integration review |
| R4-R6 | BLOCKER | State management review |
| R7-R8 | BLOCKER | Hook + error review |
| R9-R11 | MANDATORY | Visual QA |
| R12-R13 | MANDATORY | API contract compliance |
| R14-R15 | MANDATORY | Architecture review |
| R16-R17 | STRICT | Code review |

**BLOCKER rules fail the build.** MANDATORY rules require fix before merge. STRICT rules are style/pattern guidance.
