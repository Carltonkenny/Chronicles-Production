# 00 — Bug Prevention Contract: Why AI-Generated React Breaks

> **Purpose:** Document the exact backend bugs and contract inconsistencies that cause AI-generated React code to fail. These are PROVEN issues — I read every line of the backend to find them.
>
> **Rule:** Never start frontend code until these are fixed. Every bug here WILL manifest as a cryptic frontend error.

---

## Bug 1: Missing Route Decorator — Audio Always 404s

### Proof

In `backend/main.py`, a function to serve audio files exists but is **unreachable**:

```
Line 620: @app.get("/films/{filename}")           ← HAS decorator
Line 621: async def serve_film(filename: str):     ← WORKS
...
Line 626: async def get_audio_file(story_hash: str):  ← NO @app.get decorator
Line 627:     audio_data = edge_tts_service.get_cached(story_hash)
```

The SSE `done` event emits `audio_url: "/api/audio/{story_hash}"`. The frontend requests that URL → **404 Not Found**.

### What AI Does Wrong

```typescript
// AI generated frontend will do this:
const audioUrl = doneData.audio_url  // "/api/audio/abc123"
// set src={audioUrl}
// → 404 error, silent fallback, no narration plays
```

### Prevention Rule

If you see `audio_url` in SSE data, always:
1. Expect it **may be null** (audio generation can fail gracefully)
2. Expect it **may 404** (until this backend bug is fixed)
3. Handle the null/404 case with a UI fallback ("No narration available")

---

## Bug 2: Dual "Done" Events — Frontend Navigates Too Early

### Proof

The backend emits TWO `done` events with different meanings:

```python
# showrunner.py line 255 — pct=85, data=combined (story + images, NOT complete)
yield ProgressEvent("done", "story_complete", 85, "...", combined)

# main.py line 601 — pct=100, data={audio_url, mp4_url, mode, clips}
yield f"event: done\ndata: {json.dumps({'phase': 'done', 'pct': 100, ...})}\n\n"
```

The first `done` fires before video generation even starts. The second `done` fires after the MP4 is assembled.

### What AI Does Wrong

```typescript
// AI writes:
es.addEventListener('done', (e) => {
  const data = JSON.parse(e.data)
  navigate(`/film/${data.data.story_hash}`)
  // → NAVIGATES TO VIEWER AT 85% — film doesn't exist yet!
})
```

### Prevention Rule

Listen for the second `done` event only. Ignore the first one. Backend fix: rename the showrunner's `done` to `"pipeline_complete"`.

---

## Bug 3: Hash Inconsistency — Story Preview Doesn't Map to Film

### Proof

Two different hash formulas for the same input:

```python
# main.py line 272 (in /generate-story):
story_hash = hashlib.sha256(
    f"{result.story}:{get_voice_for_culture(culture_enum.value)}".encode()
).hexdigest()[:16]
# → hash depends on the LLM OUTPUT (unknown until generation finishes)

# main.py line 380 (in /generate-film):
story_hash = hashlib.sha256(
    f"{story_request.culture.value}|{story_request.timeline.value}|{story_request.theme.value}|{story_request.seed_idea}".encode()
).hexdigest()[:16]
# → hash depends on INPUT (known before generation starts)
```

Same `seed_idea + culture + timeline + theme` → **different hashes** on the two endpoints.

### What AI Does Wrong

```typescript
// AI assumes hashes match:
const storyRes = await fetch('/api/generate-story', {...})
const storyHash = storyRes.metadata.story_hash
// Later:
await fetch('/api/generate-film', {...})
// → film gets a DIFFERENT hash, can't link preview to generation
```

### Prevention Rule

The frontend should calculate its own hash from input (not from the story response):

```typescript
function computeStoryHash(culture: string, timeline: string, theme: string, seed: string): string {
  // SHA-256 of inputs, first 16 chars
  // This matches /generate-film's hash formula
  const hash = await sha256(`${culture}|${timeline}|${theme}|${seed}`)
  return hash.slice(0, 16)
}
```

---

## Bug 4: No Catalog Endpoints — Library Has No Data

### Proof

The backend storage layer is write-only:

- `db_service.py` → only has `save_story()`. No `get_stories()`, `list_stories()`, `search_stories()`.
- `main.py` → no `GET /api/catalog`, `GET /api/films/{hash}` endpoints.
- The SSE `done` event does NOT auto-save to any database.

### What AI Does Wrong

```typescript
// AI writes a beautiful Netflix-style Library page:
function LibraryPage() {
  const [films, setFilms] = useState([])
  useEffect(() => {
    fetch('/api/catalog').then(...)  // → 404
  }, [])
  return <FilmRow films={films} />  // → empty forever
}
```

### Prevention Rule

Do NOT write the Library page until the `/api/catalog` endpoint exists. Hardcode the first library query instead:

```typescript
// Temporary: read from a local seed.json
import seedFilms from './seed-data.json'
// Permanent: switch to fetch('/api/catalog') when endpoint is live
```

---

## Bug 5: SSE Data Shapes Are Undocumented — Every Phase Is Different

### Proof

The `data` field in `ProgressEvent` is typed as `dict | None` but the actual shape changes depending on `phase + step`:

| Phase | Step | `data` shape |
|-------|------|-------------|
| `story` | any | `{}` (empty) |
| `visual_bible` | `"complete"` | Full VisualBible nested dict |
| `visual_bible` | any other | `{}` (empty) |
| `images` | `"complete"` | `{total_count, portraits, scenes, character_map}` |
| `video` | `"generation"`/`"failed"` | Video clips dict |
| `post` | `"audio_complete"` | `{audio_url: string}` |
| `post` | any other | `{}` (empty) |
| `done` | — | `{audio_url, mode, mp4_url, video_clips, total_clips}` |

### What AI Does Wrong

```typescript
// AI writes one type for all events — WRONG:
interface SSEEvent {
  phase: string
  step: string
  pct: number
  data: Record<string, any>  // "any" = bugs waiting to happen
}

// Then tries: event.data.scenes → crash on story events
// Or: event.data.visual_bible → crash on video events
```

### Prevention Rule

Use discriminated unions. TypeScript's union types are the solution:

```typescript
type SSEEvent =
  | { phase: 'story'; pct: number; data: never }
  | { phase: 'visual_bible'; step: 'complete'; pct: number; data: VisualBibleData }
  | { phase: 'visual_bible'; pct: number; data: never }
  | { phase: 'images'; step: 'complete'; pct: number; data: ImagePayload }
  | { phase: 'done'; pct: 100; data: DonePayload }
  | { phase: string; pct: number; data: unknown; error?: boolean }
```

---

## Summary: The 5 Bugs and Their Blocker Status

| Bug | Backend File | Line | Frontend Impact | Blocks What? |
|-----|-------------|------|----------------|-------------|
| #1 Missing audio route | `main.py` | 626 | Narration audio always 404s | ViewerPage audio |
| #2 Dual done events | `showrunner.py` + `main.py` | 255 + 601 | Navigates before film ready | ViewerPage video |
| #3 Hash mismatch | `main.py` | 272 vs 380 | Can't link preview to film | ForgePage cache |
| #4 No catalog endpoints | `main.py` | N/A | Library has no data | LandingPage + LibraryPage |
| #5 SSE data shape unknown | `main.py` + `showrunner.py` | All | TypeScript can't validate | SSE hook |

---

## Root Cause Pattern

All 5 bugs share the same root cause: **the frontend developers (human or AI) never read the entire backend codebase**. They assume consistent patterns, single source of truth, and documented contracts — none of which exist for this SSE stream.

**The solution is not "write better React."** The solution is:

1. Fix the 5 backend bugs first
2. Document the EXACT contract in a single source of truth (see `01-API-CONTRACT.md`)
3. Generate TypeScript types from that contract
4. Then React components become trivial — they just render what the types describe
