# ✍️ Phase 1: Core Story Pipeline (Week 3-4)

## Objective
Implement Planner → Writer → Script Supervisor pipeline with caching, Wikipedia context, stereotype detection, and Pydantic schema validation.

---

## Architecture Flow

```
User Request
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    STORY PIPELINE                            │
│                                                              │
│  ┌──────────┐     ┌──────────┐     ┌───────────────────┐    │
│  │ PLANNER  │────▶│  WRITER  │────▶│ SCRIPT SUPERVISOR │    │
│  │ (LLM #1) │     │ (LLM #2) │     │    (LLM #3)       │    │
│  └────┬─────┘     └────┬─────┘     └────────┬──────────┘    │
│       │                │                     │               │
│       │ Wikipedia      │ Story Blueprint     │ Story Text    │
│       │ Context        │                     │               │
│       │ (cached)       │                     │               │
│       ▼                ▼                     ▼               │
│  ┌──────────┐     ┌──────────┐     ┌───────────────────┐    │
│  │ Story    │     │ Full     │     │ Scene Breakdown   │    │
│  │ Blueprint│     │ Narrative│     │ (6-12 scenes)     │    │
│  │ JSON     │     │ 600-900w │     │ JSON              │    │
│  └──────────┘     └──────────┘     └───────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              STEREOTYPE SCAN (post-generation)        │   │
│  │  Pattern matching against known cultural traps        │   │
│  │  Flagged → warn, never cache                          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              CACHE CHECK (pre-computation)             │   │
│  │  story_hash = SHA256(culture|timeline|theme|seed)     │   │
│  │  If cache hit → return immediately                    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
Story Bible JSON → feeds into Phase 2 (Visual Bible)
```

---

## Ported from MVP (Nazi folder)

### planner_prompt.py (ported)
- Truby/McKee structural tradition personality
- Culture-specific stereotype trap injection
- Seed idea enforcement with retry
- 4-depth character complexity (contradiction, physical tell, object, voice)
- JSON blueprint output

### writer_prompt.py (ported)
- Adichie/Mantel/Hosseini literary tradition
- "Poetic banger lines" quality requirement
- Sensory anchoring (show through body, not statements)
- Character consistency enforcement
- 600-900 word target with pacing structure

### tools.py (ported)
- `get_wikipedia_summary()` — Wikipedia API with LRU cache (24h TTL)
- `scan_for_stereotypes()` — Pattern matching against known traps
- `get_culture_traps()` — Per-culture stereotype phrases

### json_utils.py (ported)
- `extract_and_repair_json()` — Handle LLM JSON hallucinations
- 6-stage repair pipeline (newlines, trailing commas, dict-in-array, etc.)

---

## New Components

### Script Supervisor Agent (NEW)
```
Input: Full story narrative + Blueprint
Process:
  1. Identify scene boundaries (location changes, time jumps)
  2. Extract characters per scene
  3. Estimate emotional arc per scene
  4. Calculate target duration per scene
Output: SceneBreakdown JSON
  scenes: [
    {
      "id": "scene_1",
      "number": 1,
      "summary": "Bjorn discovers star-metal in frozen river at dawn",
      "location": "frozen_river",
      "time_of_day": "dawn",
      "characters_present": ["bjorn"],
      "emotional_beat": "wonder_discovery",
      "key_action": "Bjorn pulls glowing metal from ice",
      "target_duration_s": 8,
      "narration_text": "The river held its secret beneath a sheet of ice..."
    },
    ...
  ]
```

### Cache Layer (NEW — replacing in-memory LRU)
```
Redis cache:
  Key: story:{story_hash}
  Value: StoryBible JSON
  TTL: 30 days
  
  Key: wiki:{culture}
  Value: Wikipedia summary
  TTL: 24 hours
  
  Key: traps:{culture}
  Value: stereotype patterns
  TTL: permanent
```

### Stereotype Map (ENHANCED)
```
New cultures added:
  - nazi_germany: "glorifying regime", "evil caricature", "banality of evil only"
  - indian: "mystic guru", "exotic east", "caste as destiny", "slumdog archetype"
  
Category mappings:
  nazi_germany → ["totalitarian", "generic"]
  indian → ["south_asian", "colonial_default", "generic"]
```

---

## Tasks

| # | Task | Effort | Depends On |
|---|------|--------|-----------|
| 1.1 | Port planner_prompt.py from MVP | 30m | Phase 0 |
| 1.2 | Port writer_prompt.py from MVP | 30m | Phase 0 |
| 1.3 | Port tools.py (Wikipedia + stereotype scan) | 1h | Phase 0 |
| 1.4 | Port json_utils.py (JSON repair) | 30m | Phase 0 |
| 1.5 | Implement PlannerAgent (extends BaseAgent) | 2h | 1.1, 1.3, 1.4 |
| 1.6 | Implement WriterAgent (extends BaseAgent) | 2h | 1.2, 1.4 |
| 1.7 | Write Script Supervisor prompt | 2h | — |
| 1.8 | Implement ScriptSupervisorAgent (extends BaseAgent) | 2h | 1.7 |
| 1.9 | Implement Redis caching layer | 2h | 1.5, 1.6 |
| 1.10 | Enhance stereotype map (Nazi, Indian categories) | 1h | 1.3 |
| 1.11 | Create StoryRequest/StoryOutput Pydantic models | 1h | Phase 0 |
| 1.12 | Implement cache-key computation (deterministic hash) | 30m | Phase 0 |
| 1.13 | Write Planner unit tests (mocked LLM) | 2h | 1.5 |
| 1.14 | Write Writer unit tests (mocked LLM) | 2h | 1.6 |
| 1.15 | Write Script Supervisor unit tests | 1h | 1.8 |
| 1.16 | Write integration test (Planner→Writer→Supervisor) | 2h | 1.5-1.8 |
| 1.17 | Add story generation endpoint to main.py | 1h | 1.11 |

**Total: ~22.5 hours (Week 3-4)**

---

## Verification Checklist
- [ ] `POST /api/v4/story` generates a complete Story Bible
- [ ] Same request twice → cache hit on second call
- [ ] Wikipedia context returns cached on second call
- [ ] Stereotype scan catches "horned helmets" in Viking story
- [ ] Script Supervisor extracts 6-12 scenes from 700-word story
- [ ] All agents log lineage to DB
- [ ] All unit + integration tests pass
