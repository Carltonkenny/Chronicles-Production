# 📋 RULES.md — Engineering Rules

## ABSOLUTE RULES (Never Violate)

### R1: Deterministic Everything
Every generated artifact (story, image, video) SHALL be deterministic: same inputs → same outputs. Use SHA-256 hashes as seeds. Never use `random()` or timestamp-based seeds.

### R2: Cache Before Compute
Before any LLM call, API call, or computation, check the cache. If a cache hit exists and TTL hasn't expired, return cached result. No exceptions.

### R3: Agent Timeout
Every agent SHALL have a configurable timeout (default 30s). If an agent exceeds timeout, it is killed and its parent spawns a replacement. No agent runs indefinitely.

### R4: Structured Logging
Every significant event SHALL be logged as structured JSON with at minimum: timestamp, agent_type, level, film_id, event, and context dict. No `print()` statements. Use structlog.

### R5: Graceful Degradation
No single API failure SHALL break the film production pipeline. If video generation fails: substitute static image + Ken Burns effect. If audio fails: silent film. If LLM fails: retry 2x, then fall back.

### R6: Cultural Safety Mandate
Every story SHALL pass through: (a) culture-specific stereotype trap injection into Planner prompt, (b) post-generation pattern scan, (c) human-visible flagging. Flagged stories are NEVER cached.

### R7: Signature Item Enforcement
Every character SHALL have 1-2 signature items. These items MUST appear in all generated images and videos of that character. Video QC agents SHALL reject clips missing signature items.

### R8: Agent Lineage Tracing
Every agent invocation SHALL write to the `agent_lineage` table: agent_type, parent_agent, work_order_id, film_id, status, tokens_used, wall_time_ms, confidence. This is non-negotiable — it's the observability backbone.

### R9: Schema Validation
Every inter-agent communication SHALL use Pydantic models. No passing raw dicts between agents. Validate on send AND receive.

### R10: No Hardcoded Secrets
API keys, tokens, and credentials SHALL ONLY be accessed via environment variables through the Config dataclass. Validation at startup crashes fast if missing.

---

## WORKFLOW RULES

### WR1: Work Order Protocol
Every agent receives a WorkOrder and returns a WorkResult. Both are Pydantic models. No other communication pattern between agents.

### WR2: Retry Budget
Maximum 2 retries per work order. After 2 failures, parent agent receives error result and decides: substitute, degrade, or abort film.

### WR3: Parallel Where Possible
Any agents at the same level with no data dependencies SHALL run in parallel via `asyncio.gather`. Sequential execution is only for true dependencies.

### WR4: Semaphore Limits
Maximum concurrent LLM calls: 8-10 for free tier, configurable. Maximum concurrent video API calls: 4 for free tier. Exceeding these triggers rate limiting and wasted retries.

### WR5: Showrunner Has Final Authority
The Showrunner agent (Level 0) can approve, reject, or modify ANY output from ANY agent. No department head can override Showrunner.

---

## CODE RULES

### CR1: Type Hints Mandatory
Every function signature SHALL include type hints. Every Pydantic model SHALL have field descriptions. No `Any` types without explicit justification.

### CR2: Async By Default
All I/O-bound operations (LLM calls, API calls, DB queries, file operations) SHALL be async. Use `async/await`. Use `httpx.AsyncClient`. Use `asyncio.gather` for parallel execution.

### CR3: Function Length
Maximum function length: 40 lines. If longer, extract helper functions. Exception: complex prompts (which are data, not logic) can be longer.

### CR4: File Length
Maximum file length: 500 lines. If longer, split into modules. Exception: prompt files can be up to 800 lines.

### CR5: No Relative Imports Beyond Parent
Use absolute imports from project root. No `from ....some.module import thing`.

### CR6: Constant Naming
All constants in UPPER_SNAKE_CASE. All config values in a single Config dataclass. No magic numbers — use named constants.

---

## DATABASE RULES

### DR1: PostgreSQL Only (Supabase)
SQLite is legacy. All new code uses PostgreSQL via Supabase client or async SQLAlchemy. Migrations via Alembic.

### DR2: JSONB for Unstructured
All agent outputs (blueprint, story, visual bible, work orders) go into JSONB columns. Never try to normalize deeply nested agent outputs.

### DR3: Index Story Hashes
Every table with a `story_hash` column SHALL have an index on it. Primary lookup pattern.

### DR4: Soft Deletes
Never hard-delete a film or story. Use a `deleted_at` timestamp for soft deletes. Agent lineage is immutable (never deleted).

---

## API RULES

### AR1: SSE for Progress
Film generation is long-running (2-3 minutes). Use Server-Sent Events to stream progress updates to the frontend. No polling endpoints.

### AR2: Idempotent Film Creation
POST `/api/generate-film` with same parameters returns same film (from cache if exists). Use story_hash as idempotency key.

### AR3: Rate Limiting
All endpoints SHALL have rate limiting via slowapi. Free tier: 10 req/hour. Configurable per tier.

### AR4: CORS Configuration
Only configured frontend origins. No `*` in production.

---

## FRONTEND RULES

### FR1: No Frameworks
Vanilla JavaScript SPA. No React, Vue, Svelte, or build tools. The MVP proved this works; production scales it.

### FR2: Modular CSS
One CSS file per component. Import order: layout.css → components.css → view-specific.css. Glassmorphism dark theme baseline.

### FR3: Lazy Load Videos
Don't load video files until user clicks play. Show thumbnail + title card first. Use Cloudflare R2 URLs for all media.

### FR4: Accessible Player
Video player MUST have: play/pause, volume, fullscreen, chapter navigation, progress scrubber, narration toggle. Keyboard accessible.

---

## DEPLOYMENT RULES

### DEP1: Docker Multi-Stage Builds
Backend Dockerfile uses multi-stage: builder (install deps) → runner (minimal image). No dev dependencies in production image.

### DEP2: Health Checks
Every service SHALL have `/health` endpoint returning JSON with status of: DB connection, LLM API reachability, image API reachability, video API reachability.

### DEP3: Graceful Shutdown
FastAPI app SHALL handle SIGTERM gracefully: stop accepting new requests, complete in-flight generations (with timeout), close DB connections, exit.

---

## NAMING CONVENTIONS

| Entity | Convention | Example |
|--------|-----------|---------|
| Python files | snake_case | `video_prompt_crafter.py` |
| Python classes | PascalCase | `VideoPromptCrafter` |
| Python functions | snake_case | `craft_video_prompt()` |
| Python constants | UPPER_SNAKE_CASE | `MAX_RETRIES` |
| DB tables | snake_case | `story_bibles` |
| DB columns | snake_case | `story_hash` |
| API endpoints | kebab-case | `/api/generate-film` |
| CSS classes | kebab-case | `character-gallery` |
| JS functions | camelCase | `createFilm()` |
| JS files | kebab-case | `hero-carousel.js` |
| JSON keys | snake_case | `"work_order_id"` |
| Env vars | UPPER_SNAKE_CASE | `POLLINATIONS_MODEL` |

---

## PRIORITY MATRIX

When making decisions, use this priority order:

1. **Safety** — Never generate harmful cultural content
2. **Determinism** — Same input = same output
3. **Caching** — Don't recompute what's cached
4. **Cost** — Free tier viability over paid features
5. **Quality** — Output quality over speed
6. **Speed** — Parallel over sequential
7. **UX** — Netflix-style over functional
