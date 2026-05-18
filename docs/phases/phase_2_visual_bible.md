# 🎨 Phase 2: Visual Bible (Week 5-6)

## Objective
Implement Director → Production Designer → Art Director pipeline that creates the Visual Bible — the single source of truth for all downstream visual generation.

---

## Architecture Flow

```
Story Bible (from Phase 1)
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    VISUAL BIBLE PIPELINE                     │
│                                                              │
│  ┌──────────────┐   ┌────────────────┐   ┌──────────────┐   │
│  │  DIRECTOR    │──▶│   PRODUCTION   │──▶│     ART      │   │
│  │  (LLM #4)    │   │   DESIGNER     │   │   DIRECTOR   │   │
│  │              │   │   (LLM #5)     │   │   (LLM #6)   │   │
│  └──────┬───────┘   └───────┬────────┘   └──────┬───────┘   │
│         │                   │                    │          │
│         │ Overall vision    │ World-building     │ Props    │
│         │ Pacing & tone     │ Materials & colors │ Motifs   │
│         │ Signature items   │ Architecture       │ Symbols  │
│         │ Shot matrix       │ Lighting schemes   │ Details  │
│         ▼                   ▼                    ▼          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              VISUAL BIBLE (JSON, 5-10KB)              │   │
│  │                                                       │   │
│  │  {                                                    │   │
│  │    "film_tone": "Dark, brooding, fire-lit",           │   │
│  │    "pacing": "Slow discovery → frantic obsession",    │   │
│  │    "color_palette": ["#2C1810", "#D4451A", "#8B9DC3"],│   │
│  │    "lighting_style": "Low-key, fire-primary, deep     │   │
│  │                       shadows, rim highlights",        │   │
│  │    "camera_language": "35mm wide establishing → 85mm  │   │
│  │                        close-up tension → 50mm normal",│   │
│  │    "character_bibles": {                              │   │
│  │      "bjorn": {                                       │   │
│  │        "appearance": "40s, steel-gray eyes...",       │   │
│  │        "signature_items": ["boar-head hammer",        │   │
│  │                            "jagged temple scar"],      │   │
│  │        "costume": "soot-stained leather tunic...",    │   │
│  │        "emotional_range": "wonder→obsession→remorse"   │   │
│  │      }                                                │   │
│  │    },                                                 │   │
│  │    "locations": {                                     │   │
│  │      "frozen_river": {                                │   │
│  │        "architecture": "Natural, ice formations,      │   │
│  │                         pine forest edge",             │   │
│  │        "materials": ["ice", "dark water", "pine"],     │   │
│  │        "time_lighting": "dawn, cold blue ambient,     │   │
│  │                          warm orange star-metal glow"  │   │
│  │      }                                                │   │
│  │    },                                                 │   │
│  │    "shot_variation_matrix": {                         │   │
│  │      "scene_1": {                                     │   │
│  │        "shot_1": "Wide river establishing, 35mm",     │   │
│  │        "shot_2": "Medium Bjorn discovery, 50mm",      │   │
│  │        "shot_3": "Close-up star-metal glow, 85mm"     │   │
│  │      }                                                │   │
│  │    },                                                 │   │
│  │    "emotion_to_camera_map": {                         │   │
│  │      "wonder": "slow push-in, shallow DOF",           │   │
│  │      "obsession": "dutch angle, tight framing",       │   │
│  │      "remorse": "high angle, wide, small in frame"    │   │
│  │    }                                                  │   │
│  │  }                                                    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
Visual Bible → feeds Phase 3 (Images) + Phase 4 (Video)
```

---

## Agent Details

### Director Agent
```
Role: Overall creative vision
Input: Story Bible (title, narrative, scene breakdown, characters)
Output: Film tone, pacing, signature items per character, shot matrix
  
DO:
  ✅ Create 1-2 Signature Items per character (MUST be unique, story-relevant)
  ✅ Define emotional arc → camera language mapping
  ✅ Specify shot variation: each shot must be unique (angle/lighting/distance)
  ✅ Connect DB context to specific story elements

DON'T:
  ❌ Create generic visual rules (must be story-specific)
  ❌ Forget signature items (MANDATORY for character recognition)
  ❌ Make all shots look the same
  ❌ Exceed 10KB Visual Bible (keeps broadcast efficient)
```

### Production Designer Agent
```
Role: World-building — materials, colors, architecture
Input: Story Bible + Director's vision + DB visual_elements
Output: Per-location architecture, materials, color theory, lighting

DO:
  ✅ Use specific materials from visual_elements table
  ✅ Define color palette per location (hex codes, not names)
  ✅ Match lighting to emotional arc (warm for hope, cool for loss)
  ✅ Reference real historical/cultural architecture

DON'T:
  ❌ Use generic materials ("stone" → "limestone" or "granite")
  ❌ Invent colors outside DB palette
  ❌ Ignore time of day in story
```

### Art Director Agent
```
Role: Props, motifs, symbols, set dressing
Input: Story Bible + Production Designer's world + DB visual_elements
Output: Prop list per scene, cultural symbols, motif descriptions

DO:
  ✅ Every prop must be culturally accurate
  ✅ Symbols must have story significance (not random)
  ✅ Signature items must be included in relevant props
  ✅ Use visual_elements.artifact data

DON'T:
  ❌ Add anachronistic props (no smartphones in Bronze Age)
  ❌ Use generic descriptions ("a weapon" → "a bronze-tipped spear")
  ❌ Overload scenes with props (3-5 key items per scene max)
```

---

## Database Dependencies

Visual elements are generated on-demand via `VisualElementsEngine`, not pre-seeded.

**Architecture decision**: The DB `fallback_text` (1,600-2,200 chars per culture) provides rich cultural context. The LLM generates structured visual elements from this context + Wikipedia (skipped silently if unavailable). Results are cached in Redis (90-day TTL). The `visual_elements` table in SQLite is an optional enrichment layer — it may contain pre-validated data for some combos, but the engine works without it.

**Why not pre-seed 100+ combos**: 6 hours of manual curation saves one 10-second LLM call per film. Break-even requires thousands of films. The engine covers 100% of combos immediately and self-enriches over time.

---

## Tasks

| # | Task | Effort | Depends On |
|---|------|--------|-----------|
| 2.1 | Write Director prompt | 2h | — |
| 2.2 | Write Production Designer prompt | 2h | — |
| 2.3 | Write Art Director prompt | 2h | — |
| 2.4 | Create VisualBible Pydantic schema | 2h | — |
| 2.5 | Implement DirectorAgent (extends BaseAgent) | 2h | 2.1, 2.4 |
| 2.6 | Implement ProductionDesignerAgent | 2h | 2.2, 2.4 |
| 2.7 | Implement ArtDirectorAgent | 2h | 2.3, 2.4 |
| 2.8 | Implement VisualBible pipeline (sequential: D→PD→AD) | 2h | 2.5-2.7 |
| 2.9 | DB query wrapper for visual_elements | 1h | Phase 0 |
| 2.10 | Cache Visual Bible (keyed by culture|timeline|theme) | 1h | 2.8 |
| 2.11 | Seed visual_elements table (100 combos) | 6h | Phase 0 |
| 2.12 | Write Director unit tests | 1h | 2.5 |
| 2.13 | Write Production Designer unit tests | 1h | 2.6 |
| 2.14 | Write Art Director unit tests | 1h | 2.7 |
| 2.15 | Write integration test (D→PD→AD pipeline) | 1h | 2.8 |

**Total: ~28 hours (Week 5-6)**

---

## Verification Checklist
- [ ] Director creates signature items for all characters
- [ ] Production Designer outputs hex color codes, not color names
- [ ] Art Director props match culture×timeline combination
- [ ] Visual Bible validates against Pydantic schema
- [ ] Same story → cached Visual Bible (no regeneration)
- [ ] Visual Bible < 10KB (efficient broadcast to crews)
- [ ] All 100 visual_elements combos seeded in DB
