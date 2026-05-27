# 05 — Backend Fixes Required Before Frontend

> **Purpose:** 5 concrete bugs in `backend/` that will break the frontend. Each fix includes the exact file, line number, current code, fixed code, and estimated time. Apply these in order before writing any React code.
>
> **Order matters:** Fix 1-3 are 2-minute changes. Fix 4 is the only substantial one (2 hours). Do them in order.

---

## Bug 1: Missing Route Decorator on Audio Endpoint

**Severity:** BLOCKER — narration never plays
**File:** `backend/main.py`
**Line:** 626
**Time:** 2 minutes

**Problem:** The `get_audio_file` function has no `@app.get` decorator. It's unreachable dead code. The SSE `done` event emits `audio_url: "/api/audio/{story_hash}"` which always 404s.

**Current code (lines 620-642):**
```python
@app.get("/films/{filename}")
async def serve_film(filename: str):
    file_path = Path("generated") / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Film not found")
    return FileResponse(str(file_path), media_type="video/mp4")

async def get_audio_file(story_hash: str):       # ← BUG: missing @app.get
    audio_data = edge_tts_service.get_cached(story_hash)
    if not audio_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio not found"
        )
    return Response(
        content=audio_data,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f"inline; filename={story_hash}.mp3",
            "Content-Length": str(len(audio_data)),
            "Accept-Ranges": "bytes"
        }
    )
```

**Fix — add one line:**
```python
@app.get("/api/audio/{story_hash}")              # ← ADD THIS LINE
async def get_audio_file(story_hash: str):
```

---

## Bug 2: Dual "Done" Events

**Severity:** BLOCKER — frontend navigates to viewer before film is ready
**Files:** `backend/agents/showrunner.py` + `backend/main.py`
**Lines:** showrunner.py:255, main.py:433, main.py:601
**Time:** 30 minutes

**Problem:** The showrunner emits a `ProgressEvent("done", ...)` at pct=85 (before video generation). Then main.py also emits `event: done` at pct=100 (after assembly). The frontend gets confused — which "done" triggers navigation? The first one fires when only story+images are ready.

**Current code in showrunner.py (line 255):**
```python
yield ProgressEvent("done", "story_complete", 85, "All phases complete — final assembly", combined)
```

**Fix — rename to `pipeline_complete`:**
```python
yield ProgressEvent("pipeline_complete", "story_complete", 85, "All phases complete — final assembly", combined)
```

**Current code in main.py (lines 433-449):**
```python
if event.phase == "done":
    combined = event.data or {}
    # ... handles the done event, extracts images ...
    yield f"event: images\ndata: {json.dumps(...)}\n\n"
    continue
yield f"event: {event.phase}\ndata: {json.dumps(event.to_dict())}\n\n"
```

**Fix — change the condition to match:**
```python
if event.phase == "pipeline_complete":
    combined = event.data or {}
    # ... same code ...
    continue
yield f"event: {event.phase}\ndata: {json.dumps(event.to_dict())}\n\n"
```

Now the frontend only sees `event: done` at pct=100 (line 601). One done, one handler, no confusion.

---

## Bug 3: Hash Inconsistency Between Endpoints

**Severity:** HIGH — can't link story preview to film generation
**File:** `backend/main.py`
**Lines:** 272-274 (wrong), 380-382 (correct)
**Time:** 5 minutes

**Problem:** Two different hash formulas for the same input. `/generate-story` hashes the LLM output (not known until after generation). `/generate-film` hashes the input (known before generation). This means:
- The story preview can't tell you the film hash
- You can't check cache before generating
- The frontend needs two different hash calculations

**Current code (lines 272-274) — WRONG formula, uses output:**
```python
story_hash = hashlib.sha256(
    f"{result.story}:{get_voice_for_culture(culture_enum.value)}".encode()
).hexdigest()[:16]
```

**Fix — change to input-based formula (matching /generate-film):**
```python
story_hash = hashlib.sha256(
    f"{culture_enum.value}|{timeline_enum.value}|{theme_enum.value}|{request.seed_idea}".encode()
).hexdigest()[:16]
```

Now both endpoints produce the same hash for the same input. The frontend can compute the hash client-side with:
```
SHA256("{culture}|{timeline}|{theme}|{seed_idea}")[:16]
```

---

## Bug 4: No Catalog Endpoints

**Severity:** BLOCKER — Netflix-style app has no data
**Files:** `backend/main.py` (new endpoints needed), `backend/db_service.py` (new queries needed)
**Time:** 2 hours

**Problem:** The storage layer is write-only. `db_service.py` has `save_story()` but no read queries. There are no endpoints to list films, search, filter, or get film details. The Netflix catalog needs 3 new endpoints.

### 4a: New Films Table (SQLite)

Add to `backend/db_setup/schema.sql`:
```sql
CREATE TABLE films (
    story_hash TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    seed_idea TEXT NOT NULL,
    culture TEXT NOT NULL,
    timeline TEXT NOT NULL,
    theme TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'historical',
    setting TEXT,
    narrative TEXT,
    theme_reflection TEXT,
    word_count INTEGER,
    thumbnail_url TEXT,
    scene_images TEXT,          -- JSON array of URLs
    character_portraits TEXT,   -- JSON array of URLs
    video_path TEXT,
    narration_path TEXT,
    agent_count INTEGER,
    generation_time_ms INTEGER,
    status TEXT DEFAULT 'completed',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT
);

CREATE INDEX idx_films_culture ON films(culture);
CREATE INDEX idx_films_timeline ON films(timeline);
CREATE INDEX idx_films_theme ON films(theme);
CREATE INDEX idx_films_created ON films(created_at DESC);
```

### 4b: New Endpoints in main.py

```python
from typing import Optional
from pydantic import BaseModel

# --- Catalog Models ---

class FilmSummary(BaseModel):
    story_hash: str
    title: str
    culture: str
    timeline: str
    theme: str
    mode: str
    thumbnail_url: Optional[str] = None
    duration: int = 90
    created_at: str

class CatalogRow(BaseModel):
    id: str
    title: str
    type: str              # "culture" | "theme" | "timeline" | "staff_picks" | "new_releases"
    films: list[FilmSummary]

class CatalogResponse(BaseModel):
    films: list[FilmSummary]
    rows: list[CatalogRow]

class FilmDetail(BaseModel):
    story_hash: str
    title: str
    seed_idea: str
    culture: str
    timeline: str
    theme: str
    mode: str
    setting: Optional[str] = None
    narrative: Optional[str] = None
    theme_reflection: Optional[str] = None
    word_count: int = 0
    character_portraits: list[str] = []
    scene_images: list[str] = []
    video_url: Optional[str] = None
    narration_url: Optional[str] = None
    agent_count: int = 0
    generation_time_ms: int = 0
    created_at: str


# --- Auto-save film on generation complete ---

# In the `/generate-film` endpoint, after the film is assembled (line 601),
# save the film to the catalog:
@app.post("/generate-film")
async def generate_film(...):
    async def event_stream():
        # ... existing code ...
        
        # After assembly succeeds (before the done event):
        try:
            save_film_to_catalog(
                story_hash=story_hash,
                title=story_title,
                seed_idea=story_request.seed_idea,
                culture=story_request.culture.value,
                timeline=story_request.timeline.value,
                theme=story_request.theme.value,
                mode=mode,
                setting=story_data.get("setting", ""),
                narrative=story_text,
                thumbnail_url=images_payload.get("setting") if 'images_payload' in dir() else None,
                scene_images=images_payload.get("scenes", []) if 'images_payload' in dir() else [],
                character_portraits=list(ref_images.values()) if 'ref_images' in dir() else [],
                video_path=mp4_url,
                narration_path=audio_url,
                agent_count=35,  # approximate
                generation_time_ms=0,  # not tracked yet
            )
        except Exception as e:
            logger.warning(f"Failed to save film to catalog: {e}")
        
        # ... existing done event ...
```

### 4c: Catalog Endpoints

```python
import sqlite3
from pathlib import Path

DB_PATH = Path("backend/chronicles.db")


@app.get("/api/catalog", response_model=CatalogResponse)
async def get_catalog(
    culture: Optional[str] = None,
    timeline: Optional[str] = None,
    theme: Optional[str] = None,
    query: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
):
    """Get all films with optional filters. Returns both flat list and pre-computed rows."""
    
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Build dynamic WHERE clause
    conditions = ["status = 'completed'"]
    params = []
    if culture:
        conditions.append("culture = ?")
        params.append(culture)
    if timeline:
        conditions.append("timeline = ?")
        params.append(timeline)
    if theme:
        conditions.append("theme = ?")
        params.append(theme)
    if query:
        conditions.append("(title LIKE ? OR seed_idea LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%"])
    
    where = " AND ".join(conditions) if conditions else "1=1"
    
    # Get total count
    cursor.execute(f"SELECT COUNT(*) FROM films WHERE {where}", params)
    total = cursor.fetchone()[0]
    
    # Get films
    cursor.execute(
        f"SELECT * FROM films WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        [*params, limit, (page - 1) * limit]
    )
    films = [dict(row) for row in cursor.fetchall()]
    
    # Build rows (grouped by culture, theme, timeline)
    rows = []
    
    # Staff Picks row (most recent 10)
    cursor.execute("SELECT * FROM films WHERE status='completed' ORDER BY created_at DESC LIMIT 10")
    staff_picks = [dict(row) for row in cursor.fetchall()]
    if staff_picks:
        rows.append({
            "id": "staff_picks",
            "title": "Staff Picks",
            "type": "staff_picks",
            "films": staff_picks
        })
    
    # Culture rows
    cursor.execute("SELECT DISTINCT culture FROM films WHERE status='completed' ORDER BY culture")
    cultures = [row[0] for row in cursor.fetchall()]
    for culture_val in cultures:
        cursor.execute(
            "SELECT * FROM films WHERE status='completed' AND culture=? ORDER BY created_at DESC LIMIT 10",
            [culture_val]
        )
        culture_films = [dict(row) for row in cursor.fetchall()]
        if culture_films:
            display = culture_val.replace("_", " ").title()
            rows.append({
                "id": f"culture_{culture_val}",
                "title": f"{display} Stories",
                "type": "culture",
                "films": culture_films
            })
    
    # Theme rows (grouped)
    THEME_GROUPS = {
        "Power & Corruption": ["corruption", "justice"],
        "Love & Desire": ["forbidden_love", "jealousy"],
        "Survival & Identity": ["survival", "identity", "truth", "memory"],
        "Psychological": ["ambition", "betrayal", "loss", "redemption", "discovery", "obsession", "deception"],
    }
    for group_title, theme_values in THEME_GROUPS.items():
        placeholders = ",".join("?" * len(theme_values))
        cursor.execute(
            f"SELECT * FROM films WHERE status='completed' AND theme IN ({placeholders}) ORDER BY created_at DESC LIMIT 10",
            theme_values
        )
        theme_films = [dict(row) for row in cursor.fetchall()]
        if theme_films:
            rows.append({
                "id": f"theme_{group_title.lower().replace(' ', '_')}",
                "title": group_title,
                "type": "theme",
                "films": theme_films
            })
    
    conn.close()
    
    return {"films": films, "rows": rows, "total": total}


@app.get("/api/films/{story_hash}", response_model=FilmDetail)
async def get_film_detail(story_hash: str):
    """Get full film detail including story, images, and video URLs."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM films WHERE story_hash=?", [story_hash])
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Film not found")
    
    film = dict(row)
    
    # Parse JSON fields
    import json
    film["character_portraits"] = json.loads(film.get("character_portraits", "[]"))
    film["scene_images"] = json.loads(film.get("scene_images", "[]"))
    
    return film
```

---

## Bug 5: SSE `data` Shapes Are Undocumented

**Severity:** MEDIUM — causes TypeScript confusion and runtime crashes
**Files:** `backend/main.py`, `backend/agents/showrunner.py`
**Time:** 1 hour

**Problem:** The `ProgressEvent.data` field is typed as `dict | None` but the actual shape changes depending on `phase + step`. A frontend developer reading the code cannot know what shape `data` is at any given event.

**Fix — normalize to always include `data` and add an `error` field:**

```python
# In showrunner.py — send data even when empty, add error flag
class ProgressEvent:
    phase: str
    step: str
    pct: int
    message: str
    data: dict
    error: bool

    def __init__(self, phase: str, step: str, pct: int, message: str, data: dict | None = None, error: bool = False):
        self.phase = phase
        self.step = step
        self.pct = pct
        self.message = message
        self.data = data or {}
        self.error = error

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "step": self.step,
            "pct": self.pct,
            "message": self.message,
            "data": self.data,
            "error": self.error,
        }
```

And in `main.py`, always send `data` even for progress-only events:

```python
# Change this:
yield f"event: post\ndata: {json.dumps({'phase': 'post', 'step': 'audio', 'pct': 96, 'message': 'Generating narration...'})}\n\n"

# To this (add data field even when empty):
yield f"event: post\ndata: {json.dumps({'phase': 'post', 'step': 'audio', 'pct': 96, 'message': 'Generating narration...', 'data': {}, 'error': False})}\n\n"
```

Now every SSE event has the EXACT same top-level shape. The TypeScript discriminated union works perfectly. No `Optional` fields in the top level.

---

## Summary: Fix Order

| Order | Bug | Est. Time | Frontend Impact If Skipped |
|-------|-----|-----------|---------------------------|
| 1st | Missing audio route | 2 min | Narration always 404s |
| 2nd | Dual done events | 30 min | Navigates to empty viewer |
| 3rd | Hash inconsistency | 5 min | Can't link preview to film |
| 4th | No catalog endpoints | 2 hr | Library is empty forever |
| 5th | SSE data undocumented | 1 hr | TypeScript errors everywhere |

**Total: ~3.5 hours of backend fixes** → unlocks the entire frontend build.

After these 5 fixes, the frontend has:
- A working SSE stream with predictable, typed events
- A single `done` event at the end
- A hash formula the frontend can compute client-side
- Catalog endpoints to populate the Netflix UI
- Stable, documented API contracts for every TypeScript type
