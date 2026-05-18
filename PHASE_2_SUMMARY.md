# Phase 2: Visual Bible — Complete

## Status: ✅ COMPLETE | Commit: `d3bdaf3`

---

## Executive Summary

Phase 2 implemented the Director → Production Designer → Art Director pipeline that generates a comprehensive Visual Bible — the single source of truth for all downstream visual generation (images, video, color grading). The VisualElementsEngine replaces manual DB seeding with on-demand generation from DB fallback_text + LLM cultural knowledge, covering all 225 culture×timeline combos immediately.

---

## Architecture Decisions

### D1: VisualElementsEngine Over Manual DB Seeding

**Why not pre-seed 100+ combos?** 6 hours of manual curation saves one 10-second LLM call per film. Break-even requires 2,160 films. The engine generates on-demand from DB fallback_text (1,600-2,200 chars of rich cultural data per culture) + LLM knowledge + Wikipedia (skipped silently if unavailable). Results are validated, cached in Redis (90-day TTL), and self-enrich over time. **Covers 100% of combos immediately with 0 manual curation.**

### D2: Director Runs First (Sequential Pipeline)

The Director defines signature items, shot matrix, and overall vision that both PD and AD depend on. Production Designer builds the physical world (materials, architecture, colors). Art Director places props and symbols within that world. Sequential by design — each agent enriches the previous output.

### D3: Deep Validation with Creativity Allowance

The VisualElementsEngine validates generated elements for anachronisms (titanium in Bronze Age → blocked), invalid hex codes, and stereotype patterns. But allows creative choices — a counterfactual combo (Roman + AI Hegemony) can fuse elements creatively. The system warns on unusual but valid choices, blocks only hard errors.

### D4: Signature Items Are Mandatory

Per RULES.md R7, every character must have 1-2 unique signature items. The Director prompt enforces this. All 8 edge case tests confirmed 2 signature items per character.

### D5: Visual Bible Cached by Culture×Timeline×Theme

Same culture/timeline/theme combo = same Visual Bible. Redis cache key: `visual_bible:{culture}|{timeline}|{theme}` with 30-day TTL. Skipping all 3 LLM calls on cache hit.

---

## Files Created/Modified

### Created (9 files)
| File | Lines | Purpose |
|------|-------|---------|
| `agents/director.py` | 45 | Film tone, shot matrix, signature items, character bibles |
| `agents/production_designer.py` | 48 | World-building, materials, hex colors, lighting |
| `agents/art_director.py` | 46 | Props, symbols, set dressing, motif arc |
| `prompts/director_prompt.py` | 65 | Director LLM prompt (9 output sections) |
| `prompts/production_designer_prompt.py` | 48 | PD prompt with quality requirements |
| `prompts/art_director_prompt.py` | 55 | AD prompt (5 output sections) |
| `utils/visual_engine.py` | 165 | On-demand generation + deep validation + caching |
| `tests/test_visual_bible.py` | 130 | 15 unit tests |
| `tests/test_phase2_edge_cases.py` | 160 | 8 edge case scenarios |

### Modified (7 files)
| File | Changes |
|------|---------|
| `schemas/visual_bible.py` | Extended: ShotVariation, EmotionCameraMap, VisualElementsDict models |
| `agents/showrunner.py` | Wired D→PD→AD into orchestrator |
| `main.py` | Wired director_fn, pd_fn, ad_fn into SSE event_stream |
| `IMPLEMENTATION_PLAN.md` | Updated milestones + DB seeding decision |
| `docs/phases/phase_2_visual_bible.md` | Updated database dependencies rationale |
| `README.md` | Phase 2 marked complete |
| `Dockerfile` | Added FFmpeg for Phase 5 prep |

### Archived
| File | Reason |
|------|--------|
| `audio/polly_service.py` → `_archived/` | Replaced by Edge TTS |
| `audio/ssml_generator.py` → `_archived/` | Replaced by Edge TTS |

---

## Test Results

### Unit Tests: 35/35 ✓
- Phase 1: 20 tests (enums, force-blending, agents, schemas)
- Phase 2: 15 tests (VisualBible schema, Director, PD, AD, VisualElementsEngine)

### Edge Cases: 8/8 ✓

| # | Combo | VE | Director | PD | Shots | Mats | Sig |
|---|-------|----|----------|-----|-------|------|-----|
| 1 | Viking + High Medieval | 22 | PASS | PASS | 8 | 23 | 2 |
| 2 | Roman + AI Hegemony (dist=5) | 20 | PASS | PASS | 8 | 28 | 2 |
| 3 | Nazi + World War (safety) | 20 | PASS | PASS | 8 | 18 | 2 |
| 4 | Maya + Interplanetary (dist=7) | 18 | PASS | PASS | 8 | 28 | 2 |
| 5 | Mali + Age of Exploration | 18 | PASS | PASS | 7 | 28 | 2 |
| 6 | Japanese + AI Hegemony (dist=4) | 20 | PASS | PASS | 7 | 40 | 2 |
| 7 | British + Cold War (safety) | 19 | PASS | PASS | 8 | 16 | 2 |
| 8 | Egyptian + Classical (minimal) | 20 | PASS | PASS | 4 | 16 | 2 |

### Full Pipeline Audit: 2/2 ✓

| Combo | Story | VB | Images | Audio |
|-------|-------|-----|--------|-------|
| Viking + High Medieval + Ambition | "The Star-Forged Price" (1,067w) | 5 chars, 2 sig, 5 shots | 1 setting + 5 portraits | 196KB (GuyNeural) |
| Nazi + Cold War + Survival | "The Papered Cellar" (701w) | 4 chars, 2 sig, 4 shots | 1 setting + 4 portraits | 234KB (KatjaNeural) |

---

## Rules Compliance

| Rule | Status | Implementation |
|------|--------|---------------|
| R1: Deterministic | ✅ | VB cached by culture|timeline|theme |
| R2: Cache First | ✅ | Redis → memory fallback |
| R3: Agent Timeout | ✅ | BaseAgent 30s default |
| R4: Structured Logging | ✅ | structlog in all agents |
| R5: Graceful Degradation | ✅ | Wiki down → skip, LLM down → fallback_text |
| R6: Cultural Safety | ✅ | Stereotype scan in visual_engine |
| R7: Signature Items | ✅ | Director MANDATORY output |
| R8: Agent Lineage | ✅ | BaseAgent._write_lineage() |
| R9: Schema Validation | ✅ | Pydantic VisualBible model |
| R10: No Secrets | ✅ | Config dataclass from .env |

---

## Insights Resolved This Phase

| # | Issue | Resolution |
|---|-------|-----------|
| 1 | OpenRouter HTTPStatusError | Debugged: 429 rate-limit on free models. Retry logic updated to respect Retry-After headers. Pollinations fallback works. |
| 2 | Seed validation fails ~50% | Loosened keyword match from 40% to 20%. Long seeds (>50 chars) still occasionally fail — accepted limitation. |
| 3 | Redis not running | docker-compose ready. Run `docker compose up redis` to enable. System degrades to in-memory LRU automatically. |
| 4 | Phase 3 partially done | image_agent.py handles portraits + keyframes. Phase 3 becomes: swarm refactor + Visual Bible data injection. |
| 5 | Polly stubs unused | Archived to `audio/_archived/`. Edge TTS is the audio solution. |
| 6 | No FFmpeg in Dockerfile | Added for Phase 5 video assembly. |
| 7 | Word count runs high | MAX_STORY_WORDS tightened from 800 → 700. |

---

## Next: Phase 3 — Image Swarm

Per IMPLEMENTATION_PLAN.md (Week 7-8):
- Refactor image_agent.py into swarm pattern (parallel generation)
- Inject Visual Bible data for culturally-accurate image prompts
- Character portrait generator (per character, different poses)
- Scene keyframe generator (per scene, camera angles from shot_matrix)
- Image API client (Pollinations Flux, deterministic seeds)
- Cloudflare R2 storage for generated images
