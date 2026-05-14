# 📁 Phase 0: Foundation (Week 1-2)

## Objective
Establish project structure, dependencies, database schema, config system, base agent class, and seed the 10×10×10 data.

---

## Deliverables

### 1. Project Structure
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
│   ├── main.py
│   ├── config.py
│   ├── agents/base_agent.py
│   ├── schemas/
│   ├── db/
│   ├── prompts/
│   ├── utils/
│   └── tests/
├── frontend/
├── docs/phases/
└── scripts/
```

### 2. Config System (`backend/config.py`)
```python
@dataclass(frozen=True)
class Config:
    # LLM
    OPENROUTER_API_KEY: str
    OPENROUTER_MODEL: str = "google/gemini-flash-1.5"
    POLLINATIONS_LLM_URL: str
    POLLINATIONS_MODEL: str = "gemini-fast"
    
    # Images
    POLLINATIONS_IMAGE_URL: str
    
    # Video
    VIDEO_PROVIDER: str = "runway"  # runway | pika | pollinations
    RUNWAY_API_KEY: str = ""
    PIKA_API_KEY: str = ""
    
    # Audio
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "us-east-1"
    
    # Database
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Limits
    MAX_CONCURRENT_LLM: int = 8
    MAX_CONCURRENT_VIDEO: int = 4
    AGENT_TIMEOUT_S: int = 30
    MAX_RETRIES: int = 2
    
    # Story
    MIN_STORY_WORDS: int = 500
    MAX_STORY_WORDS: int = 900
    PLANNER_TEMPERATURE: float = 0.92
    WRITER_TEMPERATURE: float = 0.75
    
    # Film
    TARGET_FILM_DURATION_S: int = 90
    CLIP_DURATION_S: int = 8
```

### 3. Database Schema (Supabase PostgreSQL)
- `cultures` — 10 rows, human-written fallback_text + traps + redirects
- `timelines` — 10 rows, human-written fallback_text + era_dates
- `themes` — 10 rows, human-written craft_notes
- `visual_elements` — 100 rows (10×10 combos), 6 categories each
- `story_bibles` — per generated story
- `visual_bibles` — per culture×timeline×theme combo
- `films` — final output records
- `agent_lineage` — every agent invocation traced

### 4. Base Agent (`backend/agents/base_agent.py`)
- Abstract base class with:
  - `work_order: WorkOrder` input
  - `result: WorkResult` output
  - `timeout_ms` config
  - `execute()` → abstract method
  - `_log_lineage()` → write to agent_lineage table
  - Cache check wrapper
  - Retry logic (max 2)

### 5. LLM Client (`backend/utils/llm_client.py`)
- Multi-provider abstraction: OpenRouter, Pollinations
- Async `call_llm(system, user, max_tokens, temperature)` → str
- Exponential backoff retry
- Token counting
- Rate limit awareness

### 6. Seed Scripts
- `scripts/seed_db.py` — Seed cultures, timelines, themes tables
- `scripts/seed_visual_elements.py` — Seed visual_elements (100 rows)

---

## Tasks

| # | Task | Effort | Depends On |
|---|------|--------|-----------|
| 0.1 | Create project structure | 1h | — |
| 0.2 | Set up pyproject.toml with dependencies | 30m | 0.1 |
| 0.3 | Create Config dataclass + .env.example | 30m | 0.2 |
| 0.4 | Create database schema (SQL) | 2h | 0.3 |
| 0.5 | Set up Supabase project + run migrations | 1h | 0.4 |
| 0.6 | Implement BaseAgent class | 2h | 0.3 |
| 0.7 | Implement LLM client abstraction | 3h | 0.3 |
| 0.8 | Implement WorkOrder/WorkResult schemas | 1h | 0.3 |
| 0.9 | Implement culture/timeline/theme enums | 30m | 0.3 |
| 0.10 | Write seed_db.py + seed data | 4h | 0.5 |
| 0.11 | Write seed_visual_elements.py + data | 6h | 0.5 |
| 0.12 | Set up Redis (Upstash free tier) | 1h | 0.3 |
| 0.13 | Set up Cloudflare R2 for media storage | 1h | — |
| 0.14 | Create Dockerfile + docker-compose.yml | 1h | 0.2 |
| 0.15 | Write health check endpoint | 1h | 0.3 |
| 0.16 | Set up structlog | 30m | 0.3 |
| 0.17 | Set up slowapi rate limiting | 1h | 0.3 |
| 0.18 | Write base agent unit tests | 1h | 0.6 |
| 0.19 | Write LLM client unit tests | 1h | 0.7 |

**Total: ~28 hours (Week 1-2)**

---

## Verification Checklist
- [ ] `docker compose up` starts backend with health check
- [ ] `/health` returns all services connected
- [ ] `/api/v4/options` returns 10 cultures, 10 timelines, 10 themes
- [ ] BaseAgent subclasses can be instantiated and execute
- [ ] LLM client successfully calls OpenRouter AND Pollinations
- [ ] All 10×10=100 visual_elements rows seeded in DB
- [ ] Redis cache read/write works
- [ ] Rate limiting returns 429 after 10 requests
- [ ] Agent lineage entries write to DB
