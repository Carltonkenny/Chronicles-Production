# 🖼️ Phase 3: Image Generation Swarm (Week 7-8)

## Objective
Implement parallel character portrait + scene keyframe image generation using Pollinations Flux. These images serve as **reference frames** for Phase 4 video generation.

---

## Architecture Flow

```
Visual Bible (from Phase 2)
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│              CHARACTER LEAD (Level 1, 1 agent)              │
│              Spawns portrait generators, collects results   │
└────────────┬────────────────────┬───────────────────────────┘
             │                    │
    ┌────────▼────────┐  ┌────────▼────────┐  ┌──────────────┐
    │ PORTRAIT GEN #1 │  │ PORTRAIT GEN #2 │  │ PORTRAIT GEN#N│
    │ (Character: Bjorn)│ │ (Char: Sigrid)  │  │ (Level 2)    │
    │ Level 2, LLM    │  │ Level 2, LLM    │  │ SWARM: 4-6   │
    └────────┬────────┘  └────────┬────────┘  │ PARALLEL     │
             │                    │            └──────┬───────┘
             └────────────────────┼───────────────────┘
                                  │
                                  ▼
             ┌────────────────────────────────────────┐
             │   Pollinations Image API (Flux model)  │
             │   ALL calls PARALLEL (6-10 images)     │
             │   Deterministic seeds per story_hash   │
             └────────────────┬───────────────────────┘
                              │
                              ▼
             ┌────────────────────────────────────────┐
             │       STORE IN CLOUDFLARE R2           │
             │   portrait_bjorn_{seed}.png            │
             │   setting_forge_{seed}.png             │
             │   REFERENCE IMAGES for video phase     │
             └────────────────────────────────────────┘
```

```
Visual Bible (same data, parallel swarm)
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│              SCENE LEAD (Level 1, 1 agent)                  │
│              Spawns scene image generators, collects results│
└────────────┬────────────────────┬───────────────────────────┘
             │                    │
    ┌────────▼────────┐  ┌────────▼────────┐  ┌──────────────┐
    │ SCENE GEN #1    │  │ SCENE GEN #2    │  │ SCENE GEN #N │
    │ (River, dawn)   │  │ (Forge, night)  │  │ (Level 2)    │
    │ Level 2, LLM    │  │ Level 2, LLM    │  │ SWARM: 6-10  │
    └────────┬────────┘  └────────┬────────┘  │ PARALLEL     │
             │                    │            └──────┬───────┘
             └────────────────────┼───────────────────┘
                                  │
                                  ▼
             ┌────────────────────────────────────────┐
             │   Pollinations Image API (Flux model)  │
             │   ALL calls PARALLEL                   │
             └────────────────┬───────────────────────┘
                              │
                              ▼
             ┌────────────────────────────────────────┐
             │   STORE IN CLOUDFLARE R2               │
             │   setting_river_{seed}.png             │
             │   setting_forge_{seed}.png             │
             └────────────────────────────────────────┘
```

---

## Agent Details

### Character Portrait Generator (Level 2, per character, 4-6 parallel)

```
Input per agent:
  - Character Bible (name, appearance, signature items, costume)
  - Visual Bible (color palette, lighting style)
  - Culture + timeline context from DB

Output:
  - Optimized Pollinations Flux prompt (100-150 words)
  - Deterministic seed (character_hash + variation_index)
  - 4-6 variations per character:
    1. Full body shot (neutral pose, show full costume)
    2. Close-up portrait (emotional expression matching story beat)
    3. Action shot (from key story moment)
    4. Detail shot (signature item close-up)
    5. (optional) Emotional state variation
    6. (optional) Interaction with prop/other character

Prompt structure:
  "[Character description with EXACT appearance lock:
    steel-gray eyes, braided red beard, jagged scar left temple,
    boar-head hammer at belt, soot-stained leather tunic]
   [Pose: standing at forge, hammer mid-swing]
   [Lighting: forge fire casting warm orange glow from right,
    deep shadows on left side of face]
   [Style: cinematic, photorealistic, 85mm portrait lens,
    shallow depth of field f/2.8]
   [Color palette: #2C1810, #D4451A, #8B9DC3]
   --ar 9:16 --seed 42"
```

DO:
  ✅ Core appearance MUST match Character Bible EXACTLY
  ✅ Signature items MUST be visible in appropriate shots
  ✅ Colors from Visual Bible palette only
  ✅ Each shot UNIQUE (different angle/pose/lighting)
  ✅ Deterministic seed from story_hash

DON'T:
  ❌ Change eye color, hair, build, or scars
  ❌ Omit signature items
  ❌ Use colors outside palette
  ❌ Make all shots look the same
```

### Scene Setting Generator (Level 2, per scene, 6-10 parallel)

```
Input per agent:
  - Scene description (location, time, mood, characters)
  - Visual Bible (architecture, materials, lighting)
  - Reference image URL (if character is in scene, use their portrait)

Output:
  - Optimized Pollinations Flux prompt
  - Deterministic seed
  - Scene keyframe image (16:9 landscape)

Prompt structure:
  "[Location description: Viking forge interior, timber beams,
    soot-blackened walls, leather bellows, anvil center frame]
   [Lighting: forge fire casting warm orange light, deep shadows,
    smoke haze diffusing light]
   [Atmosphere: intense, focused, sparks flying from hammer strike]
   [Style: cinematic wide shot, 35mm lens, deep depth of field f/8]
   [Color palette: #2C1810, #D4451A, #000000]
   --ar 16:9 --seed 142"
```

---

## Reference Image Strategy (CRITICAL for Video Phase)

```
Phase 3 Images → Phase 4 Video Prompts

Character portrait (Bjorn, close-up):
  ✅ Exact appearance: steel-gray eyes, braided red beard, jagged scar
  ✅ Signature items: boar-head hammer visible at belt
  ✅ Consistent lighting: warm forge glow from right

  ↓ REFERENCE IMAGE URL passed to Video Prompt Crafter ↓

Video prompt for Scene 3:
  "Character: SAME as reference image [portrait_bjorn_42.png].
   Steel-gray eyes MUST match reference. Jagged scar visible on
   left temple. Boar-head hammer at belt. Action: striking anvil
   with hammer, sparks flying. Camera: medium shot, 50mm."
```

This is the primary mechanism for character consistency across video clips.

---

## Tasks

| # | Task | Effort | Depends On |
|---|------|--------|-----------|
| 3.1 | Write character portrait generator prompt | 2h | — |
| 3.2 | Write scene setting generator prompt | 2h | — |
| 3.3 | Implement CharacterPortraitGen agent | 2h | 3.1, BaseAgent |
| 3.4 | Implement SceneImageGen agent | 2h | 3.2, BaseAgent |
| 3.5 | Implement Pollinations image API client | 2h | Phase 0 |
| 3.6 | Implement CharacterLead (spawns portrait swarm) | 2h | 3.3, 3.5 |
| 3.7 | Implement SceneLead (spawns scene swarm) | 2h | 3.4, 3.5 |
| 3.8 | Cloudflare R2 upload integration | 2h | 3.5 |
| 3.9 | Deterministic seed generation (hash-based) | 1h | Phase 0 |
| 3.10 | Parallel execution with asyncio.gather | 1h | 3.6, 3.7 |
| 3.11 | Image result caching (keyed by prompt+seed) | 1h | 3.5 |
| 3.12 | Write portrait_gen unit tests | 1h | 3.3 |
| 3.13 | Write scene_gen unit tests | 1h | 3.4 |
| 3.14 | Write integration test (parallel swarm) | 1h | 3.10 |

**Total: ~22 hours (Week 7-8)**

---

## Verification Checklist
- [ ] 4-6 portraits per character, all with correct appearance
- [ ] 6-10 scene keyframes, all culturally accurate
- [ ] All images stored in Cloudflare R2
- [ ] Same story_hash → same images (deterministic)
- [ ] Cache hit returns existing R2 URLs (no regeneration)
- [ ] All images have correct aspect ratios (9:16 portraits, 16:9 scenes)
- [ ] Signature items visible in all character portraits
- [ ] Parallel execution: 10-16 images in < 30 seconds