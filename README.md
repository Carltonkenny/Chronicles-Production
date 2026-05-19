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
| Phase 1: Core Pipeline | ✅ Complete |
| Phase 2: Visual Bible | ✅ Complete |
| Phase 3: Image Swarm | ✅ Complete |
| Phase 4: Video Swarm | 🔜 Next |
| Phase 5: Post-Production | ⬜ Pending |
| Phase 6: Frontend | ⬜ Pending |

## Completed Components

### Phase 1: Core Pipeline
✅ 15×15×15 enum system (15 cultures, 15 timelines, 15 themes)
✅ DB fallback data seeded
✅ Force-blending mode detection + counterfactual bridge
✅ Safety constraints (nazi_germany, british_empire, spanish_empire)
✅ Planner → Writer → Script Supervisor pipeline
✅ Showrunner async generator orchestrator
✅ BaseAgent (timeout, cache, lineage)
✅ LLM client (OpenRouter → Pollinations fallback)
✅ Caching (Redis + in-memory LRU)
✅ Stereotype detection + culture traps

### Phase 2: Visual Bible
✅ Director → Production Designer → Art Director pipeline
✅ Visual Bible schema (color palette, lighting, character bibles, props, camera language)
✅ VisualElementsEngine (on-demand generation, anachronism validation, cached 90-day)
✅ Signature items enforced (RULES.md R7)
✅ 15 unit + 8 edge case + 2 pipeline audit tests

### Phase 3: Image Swarm
✅ ImageAPIClient (async Pollinations Flux, deterministic SHA256 seeds, semaphore 8)
✅ CharacterPortraitGen (3 variations per character: full body, close-up, action)
✅ SceneKeyframeGen (1 keyframe per scene, 16:9 landscape)
✅ ImageSwarmLead (parallel orchestrator, asyncio.gather)
✅ Old 657-line monolith archived
✅ 26 new tests, 61 total passing

## Next Steps

1. Phase 4: Video Generation Swarm — per-scene video prompts, multi-provider API client, quality validation
2. Phase 5: Post-Production — Editor, Sound Designer, Colorist, FFmpeg assembly
3. Phase 6: Frontend — Netflix-style SPA (Landing, Forge, Viewer, Library)
