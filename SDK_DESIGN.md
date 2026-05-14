# 🛠️ SDK DESIGN — Chronicles Production API

## Overview

The Chronicles Production SDK provides a Python client for programmatic film generation. It wraps the FastAPI backend and handles: authentication, request submission, SSE progress streaming, caching, and result retrieval.

---

## Architecture

```
Python SDK (chronicles-sdk)
    │
    ├── Client (sync + async)
    │   ├── films.generate()        → Start film production
    │   ├── films.status()          → Check progress (SSE)
    │   ├── films.get()             → Get completed film
    │   ├── films.list()            → Browse library
    │   └── films.cache_key()       → Compute story_hash
    │
    ├── Models (Pydantic)
    │   ├── FilmRequest             → seed_idea + culture + timeline + theme
    │   ├── FilmStatus              → processing | completed | failed
    │   ├── FilmOutput              → video_url + metadata + agent_lineage
    │   └── Options                 → Available cultures/timelines/themes
    │
    └── Utilities
        ├── hash_request()          → Deterministic story_hash
        └── validate_request()      → Client-side validation
```

---

## Client API

### Installation

```bash
pip install chronicles-sdk
```

### Quick Start

```python
from chronicles import ChroniclesClient, Culture, Timeline, Theme

client = ChroniclesClient()  # Reads CHRONICLES_API_URL from env

# Generate a film
film = client.films.generate(
    seed_idea="A blacksmith who forges a blade from fallen star metal",
    culture=Culture.VIKING,
    timeline=Timeline.HIGH_MEDIEVAL,
    theme=Theme.AMBITION,
    stream_progress=True  # prints progress to stdout
)

print(f"Film ready: {film.video_url}")
print(f"Duration: {film.duration_seconds}s")
print(f"Agents used: {film.agent_count}")

# Access behind-the-scenes
for agent in film.agent_lineage:
    print(f"  {agent.agent_type}: {agent.status} ({agent.wall_time_ms}ms)")
```

### Async Usage

```python
import asyncio
from chronicles import AsyncChroniclesClient

async def main():
    async with AsyncChroniclesClient() as client:
        film = await client.films.generate(
            seed_idea="A Polynesian navigator who discovers an AI satellite",
            culture=Culture.POLYNESIAN,
            timeline=Timeline.AI_HEGEMONY,
            theme=Theme.DISCOVERY
        )
        print(film.video_url)

asyncio.run(main())
```

---

## API Reference

### `ChroniclesClient`

```python
class ChroniclesClient:
    def __init__(
        self,
        api_url: str | None = None,       # Default: CHRONICLES_API_URL env
        api_key: str | None = None,        # Default: CHRONICLES_API_KEY env
        timeout: int = 300                  # Max wait for film generation
    ):
        ...
```

### `client.films.generate()`

```python
def generate(
    self,
    seed_idea: str,                        # 10-200 chars
    culture: Culture,                       # Enum
    timeline: Timeline,                     # Enum
    theme: Theme,                           # Enum
    stream_progress: bool = False,          # Print SSE progress
    on_progress: Callable | None = None,    # Custom progress callback
    wait: bool = True                       # Block until complete
) -> FilmOutput:
    ...
```

**Returns**: `FilmOutput`
```python
class FilmOutput:
    film_id: str                           # UUID
    story_hash: str                        # SHA256 of inputs
    title: str                             # Generated title
    video_url: str                         # R2 URL
    thumbnail_url: str
    duration_seconds: int
    scene_count: int
    agent_count: int
    total_cost_cents: int
    agent_lineage: list[AgentLineageEntry]
    story_text: str                        # Full narrative
    character_portraits: list[ImageRef]
    scene_keyframes: list[ImageRef]
    stereotypes_flagged: list[str]
```

### `client.films.status()`

```python
def status(
    self,
    film_id: str | None = None,
    story_hash: str | None = None
) -> FilmStatus:
    ...
```

### `client.films.get()`

```python
def get(
    self,
    film_id: str | None = None,
    story_hash: str | None = None
) -> FilmOutput:
    ...
```

### `client.films.list()`

```python
def list(
    self,
    culture: Culture | None = None,
    timeline: Timeline | None = None,
    theme: Theme | None = None,
    limit: int = 20,
    offset: int = 0,
    sort: str = "created_at"    # created_at | title | duration
) -> list[FilmPreview]:
    ...
```

### `client.options()`

```python
def options(self) -> Options:
    ...

class Options:
    cultures: list[CultureOption]     # id, name, description, preview_image_url
    timelines: list[TimelineOption]
    themes: list[ThemeOption]
```

---

## Progress Callbacks

```python
def my_progress(event: ProgressEvent):
    match event.phase:
        case "story":
            print(f"Writing story... ({event.percent}%)")
        case "visual_bible":
            print(f"Creating visual bible...")
        case "images":
            print(f"Generating {event.total} images...")
        case "videos":
            print(f"Rendering scene {event.scene_index}/{event.scene_total}...")
        case "post":
            print(f"Assembling film...")
        case "done":
            print(f"Complete! Film URL: {event.film_url}")

film = client.films.generate(
    seed_idea="...",
    culture=Culture.VIKING,
    timeline=Timeline.HIGH_MEDIEVAL,
    theme=Theme.AMBITION,
    on_progress=my_progress
)
```

---

## Caching (Client-Side)

```python
# Compute cache key without generating
cache_key = client.films.cache_key(
    seed_idea="A blacksmith...",
    culture=Culture.VIKING,
    timeline=Timeline.HIGH_MEDIEVAL,
    theme=Theme.AMBITION
)
# "a3f2b8c9d1e4..."

# Check if film exists
try:
    film = client.films.get(story_hash=cache_key)
    print(f"Cached film: {film.video_url}")
except FilmNotFound:
    print("Not yet generated")
```

---

## Error Handling

```python
from chronicles import (
    ChroniclesError,
    FilmGenerationError,
    RateLimitError,
    CultureSafetyError,
    FilmTimeoutError,
    FilmNotFound
)

try:
    film = client.films.generate(...)
except RateLimitError:
    print("Free tier limit reached. Try again tomorrow.")
except CultureSafetyError as e:
    print(f"Content flagged: {e.flags}")
except FilmTimeoutError:
    print("Film took too long. Check status later.")
except FilmGenerationError as e:
    print(f"Generation failed: {e.reason}")
```

---

## HTTP API (Backend)

The SDK wraps these endpoints:

### `POST /api/v4/generate-film`
```json
// Request
{
  "seed_idea": "A blacksmith who forges a blade from fallen star metal",
  "culture": "viking",
  "timeline": "high_medieval",
  "theme": "ambition",
  "config": {
    "narration": true,
    "music": true,
    "target_duration_s": 72
  }
}

// Response (SSE stream)
event: progress
data: {"phase": "story", "percent": 33, "message": "Writing narrative..."}

event: progress
data: {"phase": "visual_bible", "percent": 50, "message": "Creating Visual Bible..."}

event: progress
data: {"phase": "images", "percent": 66, "message": "Generating 14 images..."}

event: progress
data: {"phase": "videos", "percent": 80, "scene_index": 3, "scene_total": 10}

event: progress
data: {"phase": "post", "percent": 95, "message": "Assembling final film..."}

event: done
data: {"film_id": "uuid", "video_url": "https://r2.../film.mp4", ...}
```

### `GET /api/v4/film/{film_id}`
Returns full `FilmOutput` JSON.

### `GET /api/v4/film/status/{film_id}`
Returns `FilmStatus` JSON.

### `GET /api/v4/films?culture=viking&limit=20`
Returns paginated list of `FilmPreview` JSON.

### `GET /api/v4/options`
Returns available cultures, timelines, themes with metadata.

### `GET /health`
```json
{
  "status": "healthy",
  "checks": {
    "database": "connected",
    "llm_api": "reachable",
    "image_api": "reachable",
    "video_api": "reachable",
    "redis": "connected"
  }
}
```
