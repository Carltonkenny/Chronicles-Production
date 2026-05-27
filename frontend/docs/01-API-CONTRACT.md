# 01 — API Contract: Backend Endpoints and Data Shapes

> **Purpose:** Single source of truth for every API endpoint, request/response shape, SSE event type, and TypeScript type. Copy these types directly into `frontend/src/types.ts`. Do NOT derive types from observation — use this document.
>
> **Version:** 4.0.0
> **Base URL:** `http://localhost:8000`

---

## 1. Health & Options Endpoints

### `GET /`
**Returns:** Service root with health status.

```typescript
interface RootResponse {
  status: string       // "healthy"
  service: string      // "Chronicles Production"
  version: string      // "4.0.0"
  endpoints: {
    health: string
    options: string
    generate_story: string
  }
}
```

### `GET /health`
**Returns:** Detailed system health.

```typescript
interface HealthResponse {
  status: string              // "healthy"
  model: string               // CONFIG.POLLINATIONS_MODEL, e.g. "gemini-fast"
  api_configured: boolean
  rate_limit_tier: "anonymous" | "authenticated"
  video_provider: string      // "cloud_gpu" | "ken_burns"
  cloud_gpu_configured: boolean
}
```

### `GET /options`
**Returns:** All selectable cultures, timelines, themes grouped by category. This is the ONLY source of truth for form options.

```typescript
interface OptionsResponse {
  cultures: {
    "Historical": CultureOption[]           // 11 cultures
    "Modern / Ideological": CultureOption[]  // 4 cultures
  }
  timelines: {
    "Prehistory & Ancient": TimelineOption[]     // 3 timelines
    "Medieval & Early Modern": TimelineOption[]  // 3 timelines
    "Modern": TimelineOption[]                   // 3 timelines
    "Contemporary": TimelineOption[]             // 1 timeline
    "Near Future": TimelineOption[]              // 2 timelines
    "Collapse": TimelineOption[]                 // 2 timelines
    "Extreme Scale": TimelineOption[]            // 1 timeline
  }
  themes: {
    "Core": ThemeOption[]                    // 5 themes
    "Love & Desire": ThemeOption[]           // 2 themes
    "Power & Morality": ThemeOption[]        // 2 themes
    "Psychological": ThemeOption[]           // 2 themes
    "Survival & Resistance": ThemeOption[]   // 1 theme
    "Identity & Epistemic": ThemeOption[]    // 3 themes
  }
}

interface CultureOption { value: string; label: string }
// value examples: "roman", "egyptian", "viking", "japanese", "aztec", etc.
// value is always lowercase, underscore-separated

interface TimelineOption { value: string; label: string }
// value examples: "paleolithic", "early_bronze_age", "high_medieval", "ai_hegemony", etc.

interface ThemeOption { value: string; label: string }
// value examples: "ambition", "betrayal", "loss", "redemption", "discovery", etc.
```

---

## 2. Story Generation Endpoint

### `POST /generate-story`
**Creates a story (text only).** Use for preview. Concurrency limited to 3 simultaneous.

**Request:**
```typescript
interface StoryGenerationRequest {
  seed_idea: string   // 10-200 characters, required
  culture: string     // One of Culture enum values, e.g. "roman"
  timeline: string    // One of Timeline enum values, e.g. "paleolithic"
  theme: string       // One of Theme enum values, e.g. "betrayal"
}
```

**Success Response (200):**
```typescript
interface StoryGenerationResponse {
  success: true
  title: string                           // Story title, e.g. "The Marble Senate"
  setting: string                         // Evocative setting description (10+ chars)
  characters: string[]                    // ["Protagonist: description", "Antagonist: description"]
  story: string                           // Full narrative (350-700 words)
  theme_reflection: string                // How the theme manifested in the story
  stereotypes_flagged: string[]           // Empty if clean, flagged phrases if any
  word_count: number
  metadata: {
    culture: string
    timeline: string
    theme: string
    culture_display: string
    timeline_display: string
    theme_display: string
    stereotype_severity: "clean" | "warning" | "review"
    story_hash: string                    // 16-char hex string
    audio_ready: boolean                  // Always false from this endpoint
    culture_fallback: string
    culture_traps: string[]
    culture_redirects: string[]
    validation: {
      seed_incorporated: boolean
      theme_clear: boolean
      quality_score: number               // 0.0-1.0
    }
  }
}
```

**Error Response (400/504/500):**
```typescript
interface ErrorResponse {
  success: false
  error: string
  status_code: number
}
// HTTP 400: Invalid culture/timeline/theme value or validation error
// HTTP 504: Timeout or RuntimeError during generation
// HTTP 500: Unexpected internal error
```

---

## 3. Film Generation — SSE Stream (CRITICAL)

### `POST /generate-film`
**Full film generation. Returns SSE stream.** Rate limited to 10/hour.

**Request:** Same `StoryGenerationRequest` as `/generate-story`.

**Response:** `text/event-stream` with these headers:
```
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

### SSE Event Types — Complete Reference

Every event follows this general structure, but `data` shape changes per event:

```typescript
interface SSEEventBase {
  phase: string      // event discriminator: "story" | "visual_bible" | "images" | "video" | "post" | "done"
  step: string       // Current sub-step description
  pct: number        // 0-100, percentage complete
  message: string    // Human-readable status message
  data: unknown      // Phase-specific payload (see discriminated types below)
  error?: boolean    // true if this event represents a failure
}
```

### Event Sequence (Exact Order)

```
event: story           pct: 0   → "Creating story blueprint..."
event: story           pct: 25  → "Writing narrative..."
event: story           pct: 50  → "Breaking down scenes..."
event: story           pct: 50  → "Story ready: TITLE (N words, N scenes)"
event: visual_bible    pct: 55  → "Creating visual vision..."
event: visual_bible    pct: 58  → "Building world..."
event: visual_bible    pct: 61  → "Designing props and symbols..."
event: visual_bible    pct: 66  → "Visual Bible ready (3 agents)"  ← data HAS the visual bible
event: images          pct: 68  → "Spawning image swarm..."
event: images          pct: 85  → "Image swarm complete: N images"  ← data HAS the images
event: video           pct: 87  → "Crafting video prompts..."
event: video           pct: 95  → "Video generation complete" OR "failed"
event: post            pct: 96  → "Creating assembly timeline..."
event: post            pct: 96  → "Generating narration..."
event: post            pct: 97  → "Designing audio..."
event: post            pct: 98  → "Color grading..."
event: post            pct: 98  → "Narration ready"  ← data HAS audio_url
event: post            pct: 99  → "Assembling final MP4..."
event: done            pct: 100 → "Film complete"     ← data HAS final payload
```

### Discriminated SSEEvent Types

```typescript
// Story phase — data is ALWAYS empty
type SSEStory = {
  phase: 'story'
  step: string
  pct: number       // 0, 25, or 50
  message: string
}

// Visual Bible phase — data is ONLY non-empty on "complete" step
type SSEVisualBible = {
  phase: 'visual_bible'
  step: 'complete'
  pct: 66
  message: string
  data: VisualBiblePayload  // Full visual bible nested object
}

type SSEVisualBibleStep = {
  phase: 'visual_bible'
  step: string          // "director" | "production_design" | "art_director"
  pct: number           // 55 | 58 | 61
  message: string
}

// Images phase — data is ONLY non-empty on "complete" step
type SSEImages = {
  phase: 'images'
  step: 'complete'
  pct: 85
  message: string
  data: ImagePayload
}

type SSEImagesStep = {
  phase: 'images'
  step: 'swarming'
  pct: 68
  message: string
}

// Video phase
type SSEVideo = {
  phase: 'video'
  step: 'generation'
  pct: 95
  message: string
  data: {
    clips: VideoClip[]
  }
}

type SSEVideoFailed = {
  phase: 'video'
  step: 'failed'
  pct: 95
  message: string
  error: true
}

type SSEVideoStep = {
  phase: 'video'
  step: 'crafting'
  pct: 87
  message: string
}

// Post phase
type SSEPostAudio = {
  phase: 'post'
  step: 'audio_complete'
  pct: 98
  message: string
  data: {
    audio_url: string | null  // "/api/audio/{story_hash}" or null
  }
}

type SSEPostStep = {
  phase: 'post'
  step: 'editing' | 'sound' | 'color' | 'assembly' | 'audio'
  pct: number
  message: string
}

// Done phase — THE ONLY ONE THAT TRIGGERS NAVIGATION
type SSEDone = {
  phase: 'done'
  pct: 100
  message: 'Film complete'
  data: {
    audio_url: string | null      // "/api/audio/{story_hash}" or null
    mode: 'historical' | 'alternate_history' | 'speculative'
    video_clips: VideoClip[]
    total_clips: number
    mp4_url: string | null        // "/films/{story_hash}.mp4" or null
  }
}
```

### SSE Event Data Payload Types

```typescript
interface VisualBiblePayload {
  director?: VisualBibleDirector
  production_designer?: ProductionDesignerOutput
  art_director?: ArtDirectorOutput
}

interface VisualBibleDirector {
  film_tone: string
  pacing: string
  color_palette: {
    primary: string[]
    secondary: string[]
    accent: string[]
  }
  lighting_style: string
  character_bibles: CharacterBible[]
  location_descriptions: LocationDescription[]
  prop_list: string[]
  shot_variation_matrix: Record<string, ShotVariation[]>
  emotion_camera_map: EmotionCameraMap[]
}

interface CharacterBible {
  name: string
  role: string
  appearance: string
  costume: string
  signature_items: string[]
  emotional_range: string
  portrait_prompt: string | null
}

interface LocationDescription {
  name: string
  description: string
  materials: string[]
  lighting: string
  time_of_day: string
}

interface ShotVariation {
  shot_id: string
  shot_type: string     // "Wide establishing" | "medium" | "close-up"
  focal_length: string  // "35mm" | "50mm" | "85mm"
  movement: string
  description: string
}

interface EmotionCameraMap {
  emotion: string
  camera_style: string
}

interface ImagePayload {
  setting: string | null        // First scene URL, or null
  scenes: string[]              // Scene image URLs
  characters: Record<string, string[]>  // character_name → [portrait URLs]
  total_count: number           // Total images generated
}

interface VideoClip {
  // Shape depends on video provider output
  // Contains: scene_id, url, duration, metadata
  [key: string]: unknown
}
```

---

## 4. Static File Endpoints

### `GET /api/audio/{story_hash}`
**Returns narration audio.** Note: this route has `@app.get` set to true after the fix.

```typescript
// Success (200):
Response: audio/mpeg binary stream
Headers:
  Content-Disposition: inline; filename={story_hash}.mp3
  Content-Length: <bytes>
  Accept-Ranges: bytes

// Error (404):
{ detail: "Audio not found" }
```

### `GET /films/{filename}`
**Serves a generated MP4 film file.**

```typescript
// filename format: {story_hash}.mp4
// file path: generated/{story_hash}.mp4

// Success (200):
Response: video/mp4 binary stream

// Error (404):
{ detail: "Film not found" }
```

### `GET /api/audio/status/{story_hash}`
**Poll audio generation status.**

```typescript
interface AudioStatusResponse {
  ready: boolean      // audio file exists
  pending: boolean    // currently generating
}
```

---

## 5. Hash Calculation (CRITICAL — Consistency Matters)

The frontend needs to calculate film hashes for cache lookups. Use the INPUT-based formula:

```typescript
// SHA-256 of pipe-separated input values, first 16 hex chars
// This matches /generate-film's hash formula
// Do NOT use the /generate-story hash formula (it hashes different data)

function computeStoryHash(culture: string, timeline: string, theme: string, seedIdea: string): string {
  const input = `${culture}|${timeline}|${theme}|${seedIdea}`
  // SHA-256 → hex → first 16 characters
  // Example: "a1b2c3d4e5f6g7h8"
}
```

---

## 6. Rate Limits

| Endpoint | Limit | Behavior |
|----------|-------|----------|
| `GET /` and `GET /health` | 100/hour (global) | Returns 429 |
| `GET /options` | 100/hour (global) | Returns 429 |
| `POST /generate-story` | 100/hour + 3 concurrent | Returns 429 or waits |
| `POST /generate-film` | 10/hour per IP | Returns 429 |

On rate limit:
```typescript
// HTTP 429 response:
{
  "error": "Rate limit exceeded: 10 per 1 hour",
  "status_code": 429
}
// Header: Retry-After: 3600  (seconds until reset)
```

---

## 7. Base API Client (Copy This Into `api.ts`)

```typescript
import type {
  OptionsResponse,
  StoryGenerationRequest,
  StoryGenerationResponse,
  ErrorResponse,
  SSEEvent
} from './types'

const BASE = ''  // Vite proxy handles /api → :8000

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options
  })
  if (!res.ok) {
    const error = await res.json() as ErrorResponse
    throw new Error(error.error || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function getOptions(): Promise<OptionsResponse> {
  return fetchJson('/options')
}

export async function generateStory(req: StoryGenerationRequest): Promise<StoryGenerationResponse> {
  return fetchJson('/generate-story', {
    method: 'POST',
    body: JSON.stringify(req)
  })
}

export function generateFilmSSE(req: StoryGenerationRequest, onEvent: (e: SSEEvent) => void, onDone: () => void, onError: (err: Error) => void): EventSource {
  const params = new URLSearchParams({
    seed_idea: req.seed_idea,
    culture: req.culture,
    timeline: req.timeline,
    theme: req.theme,
  })
  
  const es = new EventSource(`/generate-film?${params}`)
  
  es.addEventListener('story', (e) => onEvent(JSON.parse(e.data)))
  es.addEventListener('visual_bible', (e) => onEvent(JSON.parse(e.data)))
  es.addEventListener('images', (e) => onEvent(JSON.parse(e.data)))
  es.addEventListener('video', (e) => onEvent(JSON.parse(e.data)))
  es.addEventListener('post', (e) => onEvent(JSON.parse(e.data)))
  es.addEventListener('done', (e) => {
    onEvent(JSON.parse(e.data))
    onDone()
  })
  es.addEventListener('error', () => onError(new Error('SSE connection failed')))
  
  return es
}
```
