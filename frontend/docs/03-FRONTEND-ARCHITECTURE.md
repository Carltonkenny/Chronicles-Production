# 03 — Frontend Architecture

> **Purpose:** Technical architecture decisions — tech stack, file structure, state management, routing, the SSE hook design, and the build toolchain. Every decision has a rationale tied to avoiding AI-generated bugs.
>
> **Core principle:** Minimal. 25 files, not 70. Each file does ONE thing and all state lives in ONE zustand store.

---

## 1. Tech Stack

| Layer | Choice | Why NOT the alternative |
|-------|--------|------------------------|
| **Framework** | React 19 | Not Next.js (we have a separate backend, don't need SSR) |
| **Build** | Vite 6 | Sub-second HMR, native ESM, simple config |
| **Routing** | React Router v7 | De facto standard, data loaders for async routes |
| **State** | Zustand | 1KB, no boilerplate, no provider nesting. Not Redux. Not Jotai. Not Context. |
| **Styling** | Tailwind CSS v4 | Utility-first generates design tokens directly from our spec. Not CSS modules, not styled-components. |
| **SSE** | Native `EventSource` | No wrapper library needed. Just addEventListener. |
| **HTTP** | Native `fetch` | Not Axios (Zustand handles state, fetch handles transport) |
| **TypeScript** | Strict mode | Union types prevent the "data is any" bug |
| **Lint** | ESLint + Prettier | Standard. Pre-configured with Vite template. |

### Why NOT Next.js

```
API layer        → Chronicles backend (FastAPI, port 8000)
Server rendering → NOT NEEDED — films are client-viewed media
File-based routes → Adds complexity for no benefit
Server Actions   → Cannot call external FastAPI backend

Next.js is for when your API is part of the Next.js server.
Our API is a separate thing. Vite SPA is simpler, faster, correct.
```

---

## 2. File Structure (25 Files)

```
frontend/
├── index.html                          # Vite entry, loads Google Fonts (Cinzel + Inter)
├── package.json                        # react, react-dom, react-router, zustand, tailwindcss
├── vite.config.ts                       # proxy /api → localhost:8000, React plugin
├── tsconfig.json                        # strict: true
├── tailwind.config.ts                   # Design token extension (colors, fonts, radius)
│
└── src/
    ├── main.tsx                         # ReactDOM.createRoot, render <App />
    ├── App.tsx                          # BrowserRouter + Routes + Navigation + Outlet
    │
    ├── types.ts                         # ALL TypeScript types from 01-API-CONTRACT.md
    ├── api.ts                           # fetch wrapper + generateFilmSSE()
    │
    ├── stores/
    │   └── use-film-store.ts            # SINGLE zustand store (catalog + generation + viewer)
    │
    ├── hooks/
    │   ├── use-generation.ts            # SSE EventSource lifecycle + append-only events
    │   └── use-catalog.ts               # Fetch catalog, filter, search, rows
    │
    ├── components/
    │   ├── FilmCard.tsx                  # 16:9 thumbnail + title + metadata
    │   ├── FilmRow.tsx                   # Horizontal scroll wrapper
    │   ├── ForgeForm.tsx                 # Creation form (seed + selects + surprise me)
    │   ├── VideoPlayer.tsx               # Video + custom controls + chapters
    │   ├── ChapterNav.tsx                # Chapter pills
    │   ├── AgentTree.tsx                # Behind-the-scenes agent lineage
    │   └── ui/
    │       ├── GlassCard.tsx             # Reusable glassmorphism container
    │       ├── PillSelect.tsx            # Styled select dropdown
    │       ├── Toast.tsx                 # Notification toast
    │       └── Spinner.tsx               # Loading indicator
    │
    └── pages/
        ├── LandingPage.tsx              # Hero + rows
        ├── ForgePage.tsx                # Creation + progress
        ├── ViewerPage.tsx               # Watch film
        └── LibraryPage.tsx              # Browse catalog

    ## CONFIG FILES (4)
    ## TYPES + API (2)
    ## STORES (1)
    ## HOOKS (2)
    ## COMPONENTS (10)
    ## PAGES (4)

    ## TOTAL: 25 files
```

---

## 3. State Management — One Zustand Store

```typescript
// stores/use-film-store.ts
// ONE store. ONE source of truth. No exceptions.

import { create } from 'zustand'
import type { FilmSummary, CatalogRow, SSEEvent, FilmDetail, GenerationRequest } from '../types'

interface FilmState {
  // === Catalog browsing ===
  films: FilmSummary[]
  rows: CatalogRow[]
  filters: { culture?: string; timeline?: string; theme?: string; query?: string }
  catalogLoading: boolean
  catalogError: string | null
  
  // === Generation (SSE stream) ===
  status: 'idle' | 'generating' | 'done' | 'error'
  events: SSEEvent[]              // Append-only. NEVER overwrite.
  errorMessage: string | null

  // === Current film being viewed ===
  currentFilm: FilmDetail | null
  filmLoading: boolean
  filmError: string | null

  // === Actions ===
  fetchCatalog: (filters?: Partial<FilmState['filters']>) => Promise<void>
  fetchFilm: (hash: string) => Promise<void>
  startGeneration: (req: GenerationRequest) => void
  addEvent: (event: SSEEvent) => void
  resetGeneration: () => void
  setStatus: (status: FilmState['status']) => void
}

export const useFilmStore = create<FilmState>((set, get) => ({
  films: [],
  rows: [],
  filters: {},
  catalogLoading: false,
  catalogError: null,
  
  status: 'idle',
  events: [],
  errorMessage: null,
  
  currentFilm: null,
  filmLoading: false,
  filmError: null,

  fetchCatalog: async (filters) => {
    set({ catalogLoading: true, catalogError: null, ...(filters ? { filters } : {}) })
    try {
      const res = await fetch(`/api/catalog/rows`)
      if (!res.ok) throw new Error('Failed to load catalog')
      const data = await res.json()
      set({ films: data.films, rows: data.rows, catalogLoading: false })
    } catch (e) {
      set({ catalogError: (e as Error).message, catalogLoading: false })
    }
  },

  fetchFilm: async (hash) => {
    set({ filmLoading: true, filmError: null })
    try {
      const res = await fetch(`/api/films/${hash}`)
      if (!res.ok) throw new Error('Film not found')
      set({ currentFilm: await res.json(), filmLoading: false })
    } catch (e) {
      set({ filmError: (e as Error).message, filmLoading: false })
    }
  },

  startGeneration: (req) => {
    set({ status: 'generating', events: [], errorMessage: null })
  },

  addEvent: (event) => {
    set((state) => ({ events: [...state.events, event] }))
  },

  resetGeneration: () => {
    set({ status: 'idle', events: [], errorMessage: null })
  },

  setStatus: (status) => set({ status }),
}))
```

### State Access Rules

```
DO:
  const films = useFilmStore(s => s.films)           ← Select specific slice
  const { events, status } = useFilmStore()           ← Destructure in component
  useFilmStore.getState().fetchCatalog()               ← Call actions from outside React

DON'T:
  const store = useFilmStore()                         ← Don't subscribe to entire store
  localStorage for generation state                    ← Don't persist transient state
  React.Context as state                               ← Zustand IS the provider
```

---

## 4. SSE Hook — The Critical Piece

This is the highest-risk integration point. The hook must:
1. Create `EventSource` on generation start
2. Listen to NAMED events (not `onmessage`)
3. Append events to store (never overwrite)
4. Close on `done`, `error`, or component unmount
5. Handle the dual-done bug (only react to pct=100)

```typescript
// hooks/use-generation.ts
// SINGLE RESPONSIBILITY: Manage EventSource lifecycle
// DEPENDENCY: uses zustand store, not local state

import { useEffect, useRef } from 'react'
import { useFilmStore } from '../stores/use-film-store'
import type { GenerationRequest, SSEEvent } from '../types'

interface UseGenerationReturn {
  start: (req: GenerationRequest) => void
  cancel: () => void
}

export function useGeneration(onComplete: (filmUrl: string) => void): UseGenerationReturn {
  const esRef = useRef<EventSource | null>(null)
  const addEvent = useFilmStore(s => s.addEvent)
  const setStatus = useFilmStore(s => s.setStatus)
  const resetGeneration = useFilmStore(s => s.resetGeneration)

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      esRef.current?.close()
      esRef.current = null
    }
  }, [])

  const start = (req: GenerationRequest) => {
    // Close any existing connection
    esRef.current?.close()
    resetGeneration()
    setStatus('generating')

    const params = new URLSearchParams({
      seed_idea: req.seed_idea,
      culture: req.culture,
      timeline: req.timeline,
      theme: req.theme,
    })

    const es = new EventSource(`/generate-film?${params}`)
    esRef.current = es

    // Handle each named event type
    // data is always JSON — parse it
    const handleEvent = (e: MessageEvent) => {
      try {
        const event: SSEEvent = JSON.parse(e.data)
        addEvent(event)
      } catch (err) {
        console.error('Failed to parse SSE event:', err)
      }
    }

    es.addEventListener('story', handleEvent)
    es.addEventListener('visual_bible', handleEvent)
    es.addEventListener('images', handleEvent)
    es.addEventListener('video', handleEvent)
    es.addEventListener('post', handleEvent)
    
    es.addEventListener('done', (e: MessageEvent) => {
      handleEvent(e)
      setStatus('done')
      
      // Extract film URL from the done event data
      try {
        const data = JSON.parse(e.data)
        const mp4Url = data.data?.mp4_url
        if (mp4Url) onComplete(mp4Url)
      } catch {}
      
      es.close()
      esRef.current = null
    })

    es.addEventListener('error', () => {
      // EventSource auto-reconnects on error
      // Only treat as failure if connection is permanently lost
      if (es.readyState === EventSource.CLOSED) {
        setStatus('error')
      }
    })
  }

  const cancel = () => {
    esRef.current?.close()
    esRef.current = null
    resetGeneration()
  }

  return { start, cancel }
}
```

---

## 5. Routing

```typescript
// App.tsx — Route structure
// No lazy loading (4 pages, total code is small)
// No auth guards (v4.0 is public/demo)

import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Navigation from './components/Navigation'  // Top nav bar
import LandingPage from './pages/LandingPage'
import ForgePage from './pages/ForgePage'
import ViewerPage from './pages/ViewerPage'
import LibraryPage from './pages/LibraryPage'

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-[#0A0A0F] text-[#F0F0F5] font-body">
        <Navigation />
        <main>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/forge" element={<ForgePage />} />
            <Route path="/film/:hash" element={<ViewerPage />} />
            <Route path="/library" element={<LibraryPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
```

---

## 6. Error Handling Pattern

Every async operation follows the same pattern:

```typescript
// TRI-STATE PATTERN — applies to ALL data fetching
// State: idle | loading | success | error

function SomePage() {
  const { films, catalogLoading, catalogError, fetchCatalog } = useFilmStore()

  useEffect(() => { fetchCatalog() }, [])

  if (catalogLoading) return <Spinner />
  if (catalogError) return <ErrorState message={catalogError} onRetry={fetchCatalog} />
  if (films.length === 0) return <EmptyState message="No films yet" />
  
  return <FilmList films={films} />
}
```

### Error Boundary

Each page is wrapped in its own error boundary:

```typescript
// A crash in ViewerPage does NOT take down LandingPage
// Each page is an independent island

<ErrorBoundary fallback={<PageError />}>
  <ViewerPage />
</ErrorBoundary>
```

---

## 7. Build Config — Vite Proxy

```typescript
// vite.config.ts
// 12 lines. Not 80.

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/films': 'http://localhost:8000',
      '/generate-story': 'http://localhost:8000',
      '/generate-film': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/options': 'http://localhost:8000',
    }
  }
})
```

---

## 8. Dependencies (package.json)

```json
{
  "name": "chronicles-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^7.0.0",
    "zustand": "^5.0.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.0.0",
    "typescript": "^5.5.0",
    "vite": "^6.0.0",
    "tailwindcss": "^4.0.0",
    "@tailwindcss/vite": "^4.0.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0"
  }
}
```

**5 runtime deps.** Not 50. No Axios, no React Query, no Redux Toolkit, no Ant Design, no MUI, no headless UI library. Just React + Router + Zustand.

---

## 9. Build Order

```
STEP 1: npm create vite@latest (React + TypeScript template)
STEP 2: npm install react-router-dom zustand tailwindcss @tailwindcss/vite
STEP 3: Configure vite.config.ts (React plugin + Tailwind plugin + API proxy)
STEP 4: Configure tailwind.config.ts (design tokens: colors, fonts, radius)
STEP 5: Create src/types.ts (copy from 01-API-CONTRACT.md)
STEP 6: Create src/api.ts (copy from 01-API-CONTRACT.md)
STEP 7: Create src/stores/use-film-store.ts
STEP 8: Create src/hooks/use-generation.ts
STEP 9-12: Create UI components (GlassCard → Spinner → Toast → PillSelect)
STEP 13-16: Create film components (FilmCard → FilmRow → VideoPlayer → ChapterNav → AgentTree)
STEP 17-20: Create pages (Landing → Forge → Viewer → Library)
STEP 21: Wire up App.tsx routing
STEP 22: Style Navigation component
```

Total: ~22 steps. Each step is ~40 minutes. Total build time: ~15 hours for a complete, working frontend.
