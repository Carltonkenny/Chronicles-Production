# Chronicles Production v4.0

AI-native film studio. Generate complete 1-1.5 minute short films from a seed idea.

## Quick Start

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r ../requirements.txt
cp .env.example .env
# Edit .env with your API keys
python main.py
```

## Status

| Phase | Status |
|-------|--------|
| Phase 0: Foundation | ✅ Complete |
| Phase 1: Core Pipeline | 🔨 In Progress |
| Phase 2: Visual Bible | ⬜ Pending |
| Phase 3: Image Swarm | ⬜ Pending |
| Phase 4: Video Swarm | ⬜ Pending |
| Phase 5: Post-Production | ⬜ Pending |
| Phase 6: Frontend | ⬜ Pending |

## Phase 1 Completed Components

✅ 15×15×15 enum system (cultures, timelines, themes)
✅ DB fallback data seeded (all 15 cultures, timelines, themes)
✅ Force-blending mode detection (counterfactual bridge for distant combos)
✅ Safety constraints (nazi_germany, british_empire, spanish_empire)
✅ Image generation agent (Pollinations Flux, 916 lines)
✅ Visual elements DB query layer
✅ Script Supervisor agent (LLM-powered scene breakdown)
✅ Showrunner agent (async generator orchestration)
✅ Config system (frozen dataclass with validation)
✅ Logger (structlog + standard fallback)
✅ Planner + Writer pipeline (battle-tested)
✅ Prompts (1000+ lines with agent personalities)
✅ JSON repair utilities (self-healing LLM output)
✅ Wikipedia integration + DB fallback cache
✅ Stereotype detection + culture traps
✅ Audio service (Polly + SSML generation)
✅ Database (SQLite with full culture/timeline/theme data)
✅ FastAPI main app (health, options, generate-story)
✅ Docker + docker-compose with Redis

## Next Steps

1. Wire Redis caching (docker-compose already configured)
2. Add SSE progress endpoint to main.py
3. Add rate limiting (slowapi)
4. Write unit + integration tests
5. Implement Phase 2: Visual Bible agents
