# 🚀 IMPLEMENTATION PLAN — Chronicles Production

## Phase 0: Foundation (Week 1-2)

### 0.1 Project Structure Setup
```
Chronicles-Production/
├── .gitignore
├── .env.example
├── README.md
├── DEEP_DIVE_PLAN.md
├── CLAUDE.md
├── RULES.md
├── IMPLEMENTATION_PLAN.md
├── PRD.md
├── SDK_DESIGN.md
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Config dataclass from env vars
│   ├── __init__.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── showrunner.py       # Level 0: Orchestrator
│   │   ├── planner.py          # Story blueprint agent
│   │   ├── writer.py           # Literary prose agent
│   │   ├── script_supervisor.py # Scene breakdown agent
│   │   └── base_agent.py       # Abstract base agent class
│   ├── director/
│   │   ├── __init__.py
│   │   ├── director.py         # Visual Bible creator
│   │   ├── production_designer.py
│   │   ├── art_director.py
│   │   └── visual_bible.py     # Visual Bible Pydantic schema
│   ├── image/
│   │   ├── __init__.py
│   │   ├── character_portrait_gen.py
│   │   ├── scene_image_gen.py
│   │   └── image_api.py        # Pollinations image API client
│   ├── video/
│   │   ├── __init__.py
│   │   ├── video_lead.py       # Level 1: Video Department Head
│   │   ├── video_prompt_crafter.py  # Level 2: Per-scene prompt
│   │   ├── video_qc.py         # Level 2: Per-clip validator
│   │   └── video_api.py        # Multi-provider video API client
│   ├── post/
│   │   ├── __init__.py
│   │   ├── editor.py           # Assembly timeline
│   │   ├── sound_designer.py   # Narration + music + SFX
│   │   ├── colorist.py         # LUT + grading
│   │   └── assembler.py        # FFmpeg orchestration
│   ├── qa/
│   │   ├── __init__.py
│   │   ├── qa_supervisor.py
│   │   ├── continuity_checker.py
│   │   ├── cultural_checker.py
│   │   └── technical_qa.py
│   ├── cache/
│   │   ├── __init__.py
│   │   └── story_cache.py      # Redis + in-memory LRU cache
│   ├── db/
│   │   ├── __init__.py
│   │   ├── supabase_client.py
│   │   ├── models.py           # SQLAlchemy models
│   │   └── migrations/         # Alembic migrations
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── planner_prompt.py
│   │   ├── writer_prompt.py
│   │   ├── script_supervisor_prompt.py
│   │   ├── director_prompt.py
│   │   ├── production_designer_prompt.py
│   │   ├── art_director_prompt.py
│   │   ├── character_portrait_prompt.py
│   │   ├── scene_image_prompt.py
│   │   ├── video_prompt_crafter_prompt.py
│   │   ├── video_qc_prompt.py
│   │   ├── editor_prompt.py
│   │   ├── sound_designer_prompt.py
│   │   └── continuity_checker_prompt.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── enums.py            # Culture, Timeline, Theme enums
│   │   ├── story.py            # StoryRequest, StoryOutput
│   │   ├── work_order.py       # WorkOrder, WorkResult
│   │   ├── visual_bible.py     # VisualBible schema
│   │   └── film.py             # FilmOutput, FilmStatus
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── llm_client.py       # Multi-provider LLM abstraction
│   │   ├── json_repair.py      # LLM JSON repair utilities
│   │   ├── wiki_context.py     # Wikipedia context fetcher
│   │   ├── stereotype_scan.py  # Pattern-based stereotype detection
│   │   └── hash_utils.py       # Deterministic hashing
│   └── tests/
│       ├── __init__.py
│       ├── test_planner.py
│       ├── test_writer.py
│       ├── test_showrunner.py
│       ├── test_director.py
│       ├── test_video_prompt.py
│       └── test_integration.py
├── frontend/
│   ├── index.html
│   ├── css/
│   │   ├── layout.css
│   │   ├── components.css
│   │   ├── forge.css
│   │   ├── library.css
│   │   ├── viewer.css
│   │   └── landing.css
│   ├── js/
│   │   ├── core/
│   │   │   ├── app.js
│   │   │   └── auth.js
│   │   ├── api/
│   │   │   └── api.js
│   │   ├── pages/
│   │   │   ├── forge.js
│   │   │   ├── library.js
│   │   │   ├── viewer.js
│   │   │   └── profile.js
│   │   └── components/
│   │       ├── hero-carousel.js
│   │       ├── chapter-selector.js
│   │       ├── character-gallery.js
│   │       ├── video-player.js
│   │       ├── agent-lineage.js
│   │       └── ui.js
│   └── assets/
│       └── .gitkeep
├── exported/                   # Useful code from old MVP
│   ├── backend/
│   │   ├── chain.py
│   │   ├── prompts.py
│   │   └── tools.py
│   └── prompts/
│       └── original_prompts.py
├── docs/
│   └── phases/
│       ├── phase_0_foundation.md
│       ├── phase_1_core_pipeline.md
│       ├── phase_2_visual_bible.md
│       ├── phase_3_image_swarm.md
│       ├── phase_4_video_swarm.md
│       ├── phase_5_post_production.md
│       └── phase_6_frontend.md
└── scripts/
    ├── seed_db.py              # Seed 10×10×10 database
    └── seed_visual_elements.py # Seed visual_elements table
```

### 0.2 Dependencies
```toml
# pyproject.toml
[project]
name = "chronicles-production"
version = "4.0.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "httpx>=0.27",
    "pydantic>=2.0",
    "python-dotenv>=1.0",
    "supabase>=2.0",
    "sqlalchemy[asyncio]>=2.0",
    "alembic>=1.13",
    "redis>=5.0",
    "structlog>=24.0",
    "slowapi>=0.1",
    "boto3>=1.34",
    "opentelemetry-api>=1.25",
    "opentelemetry-sdk>=1.25",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "pytest-cov>=5.0",
    "ruff>=0.5",
]
```

---

## Phase 1: Core Story Pipeline (Week 3-4)

### Task 1.1: Enums & Schemas
- Create Culture, Timeline, Theme enums (10 each) in `schemas/enums.py`
- Create StoryRequest, StoryOutput Pydantic models in `schemas/story.py`
- Create WorkOrder, WorkResult, AgentLineage models

### Task 1.2: LLM Client Abstraction
- Unified LLM client supporting: OpenRouter (Gemini Flash), Pollinations API
- Exponential backoff retry logic
- Token counting and cost tracking
- Configurable timeout per agent type

### Task 1.3: Base Agent Class
- Abstract base with: work_order input, result output, timeout, lineage logging
- Context manager for tracking wall_time and tokens
- Cache check before execute

### Task 1.4: Planner Agent
- Port planner_prompt.py from exported MVP
- Inject culture traps from database
- Wikipedia context fetcher (cached)
- JSON blueprint output with seed validation + retry

### Task 1.5: Writer Agent
- Port writer_prompt.py from exported MVP
- Character consistency enforcement
- Poetic prose quality requirements
- 600-900 word narrative output

### Task 1.6: Script Supervisor Agent
- NEW: Analyze completed story
- Extract scene boundaries (6-12 scenes)
- Per scene: characters present, location, emotional beat, estimated duration
- Output: Scene Breakdown JSON

### Task 1.7: Caching Layer
- Redis cache for story results (keyed by story_hash)
- In-memory LRU fallback if Redis unavailable
- Cache Wikipedia context per culture (24h TTL)
- Cache stereotype scan results

---

## Phase 2: Visual Bible (Week 5-6)

### Task 2.1: Visual Bible Schema
- Pydantic model: color_palette, lighting_style, camera_language, character_bibles, location_descriptions, prop_list, emotional_arc_to_camera_map

### Task 2.2: Director Agent
- Reads full story + scene breakdown
- Creates Visual Bible master document
- Assigns signature items to characters
- Defines shot variation matrix

### Task 2.3: Production Designer Agent
- World-building: architecture, materials, color theory
- Per-location description with specific materials
- Color palette extraction from culture data

### Task 2.4: Art Director Agent
- Props list per scene
- Cultural symbols and motifs
- Set dressing details

### Task 2.5: Database Seeding
- Seed `visual_elements` table: ALL 100 combos (10 cultures × 10 timelines)
- Each combo has: clothing (2-4 items), architecture (2-3), artifacts (3-5), lighting (2-3), hairstyles (2-3), color_palette (4-6 colors)
- Pull from enhanced Wikipedia + manual curation

---

## Phase 3: Image Generation Swarm (Week 7-8)

### Task 3.1: Character Portrait Generator
- Per character: generate detailed visual description
- Use character bible data from Visual Bible
- Include: signature items, color palette, lighting, pose, expression
- Output: optimized Pollinations Flux prompt

### Task 3.2: Scene Image Generator
- Per scene: generate keyframe description
- Include: location, time of day, lighting, camera angle, characters (if present)
- Output: optimized Pollinations Flux prompt

### Task 3.3: Pollinations Image API Client
- Async client with retry logic
- Deterministic seeding (story_hash + scene_index)
- Rate limiting awareness
- Image URL storage in Cloudflare R2

### Task 3.4: Image Swarm Orchestrator
- Spawn all portrait + scene agents in parallel
- Collect results
- Store reference images in R2
- Return image URLs to Showrunner

---

## Phase 4: Video Generation Swarm (Week 9-10)

### Task 4.1: Video Prompt Crafter Agent
- Per scene: craft optimized video prompt
- Include: reference image URL, character consistency anchors, camera movement, lighting, action description
- Support multiple video API formats (Runway, Pika, Pollinations)

### Task 4.2: Video API Client (Multi-Provider)
- Provider abstraction: Runway, Pika, Pollinations img2vid
- Async calls with retry
- Deterministic seeding per scene
- Clip storage in Cloudflare R2

### Task 4.3: Video Quality Controller Agent
- Per clip: validate against Visual Bible
- Check: signature items visible, color palette match, no hallucinated elements, action matches scene description
- Pass/Fail/Warn with specific reasons
- Failed clips → retry with modified prompt (max 2)

### Task 4.4: Video Swarm Orchestrator
- Spawn all Video Prompt Crafters in parallel
- Collect prompts → make parallel API calls
- Spawn all Video QC agents in parallel
- Handle failed clips gracefully (retry or degrade)
- Return approved clip URLs

---

## Phase 5: Post-Production (Week 11-12)

### Task 5.1: Editor Agent
- Create assembly timeline: scene order, transition types, durations
- Crossfade/cut points between scenes
- Align with narration script timing

### Task 5.2: Sound Designer Agent
- Generate narration via Amazon Polly (SSML prosody)
- Generate background music via Suno/Udio (free tier)
- Gather/procure ambient sounds per scene
- Create audio timeline

### Task 5.3: Colorist Agent
- Define color grading LUT for entire film
- Per-scene color adjustments (consistent palette)
- Scene-to-scene color continuity

### Task 5.4: FFmpeg Assembler
- Concatenate video clips (order from Editor)
- Add transitions (crossfade, hard cut)
- Overlay narration audio track
- Mix in background music + ambient
- Apply color LUT
- Add title card + credits
- Encode to MP4 (H.264, 1080p)
- Upload to Cloudflare R2

---

## Phase 6: Frontend — Netflix Style (Week 13-14)

### Task 6.1: Landing View
- Hero cinematic carousel
- Featured films (latest generated)
- Culture/Timeline/Theme showcase

### Task 6.2: Forge View (Film Creation)
- Seed idea input (text area, 10-200 chars)
- Culture selector (10 options with preview images)
- Timeline selector (10 options)
- Theme selector (10 options)
- Generate button → SSE progress stream
- Progress display: "Writing story... → Creating visuals... → Generating video... → Assembling..."

### Task 6.3: Viewer (Netflix-Style)
- Title card entry animation
- Chapter/scene selector (click to jump)
- Interactive timeline scrubber
- Character gallery (portraits + bios)
- Story text panel (sync-scrolls with video)
- Narration toggle
- Background music toggle
- Fullscreen cinema mode
- Agent lineage "Behind the Scenes" panel
- Share/copy link

### Task 6.4: Library View
- Grid of completed films
- Search by culture/timeline/theme
- Sort by date, popularity
- Film cards: thumbnail, title, duration, agent count, cost

### Task 6.5: Profile View
- User settings (if auth enabled)
- Tier status (Free/Indie/Creator)
- Generation history
- Favorite films

---

## Testing Plan

### Unit Tests (target: 80% coverage)
- Every agent: test with mocked LLM/API
- Cache: test hit/miss/eviction
- Schema validation: test edge cases
- Stereotype scan: test known patterns
- JSON repair: test LLM output edge cases

### Integration Tests
- Planner → Writer → Script Supervisor (full pipeline)
- Director → Production Designer → Art Director (Visual Bible)
- Image generation → video generation → assembly (full film)

### End-to-End Tests
- Submit request → get complete film (mock APIs)
- Cache hit → instant return
- Handle API failures gracefully

---

## Deployment Plan

### Development
```bash
docker compose up
# Backend: localhost:8000
# Frontend: localhost:3000
# Redis: localhost:6379
```

### Production (Render)
```bash
# Build
docker build -t chronicles-production .

# Deploy
render deploy --service chronicles-api
```

---

## Milestones

| Week | Milestone | Deliverable |
|------|-----------|-------------|
| 1-2 | Foundation | ✅ Complete — Project setup, DB schema, config, base agent, 15×15×15 enums |
| 3-4 | Core Pipeline | 🔨 In Progress — Force-blending, Script Supervisor, Showrunner, image agent |
| 5-6 | Visual Bible | Director → PD → AD, visual_elements seeded |
| 7-8 | Image Swarm | Character portraits + Scene keyframes |
| 9-10 | Video Swarm | 8-12 video clips, QC validated |
| 11-12 | Post-Production | FFmpeg assembly, full film output |
| 13-14 | Frontend | Netflix-style UI, full integration |

**Total: 14 weeks to production-ready MVP.**
