# 🎥 Phase 4: Video Generation Swarm (Week 9-10)

## Objective
Implement the video generation swarm — the core innovation. Per scene: craft prompt → generate clip → validate quality. All in parallel. 8-12 clips stitched into a 1-1.5 minute film.

---

## Architecture Flow

```
Scene Breakdown + Visual Bible + Reference Images (from Phase 2+3)
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│              VIDEO LEAD (Level 1, 1 agent)                  │
│              Orchestrates all video generation              │
│              Spawns Prompt Crafters + API calls + QC        │
└────────┬──────────────────┬──────────────────┬──────────────┘
         │                  │                  │
         ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ PROMPT CRAFTER  │ │ PROMPT CRAFTER  │ │ PROMPT CRAFTER  │
│ Scene 1 (River) │ │ Scene 2 (Forge) │ │ Scene N         │
│ Level 2, LLM    │ │ Level 2, LLM    │ │ SWARM: 6-12     │
└────────┬────────┘ └────────┬────────┘ │ PARALLEL        │
         │                   │          └────────┬────────┘
         └───────────────────┼───────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────┐
│              VIDEO API CALLS (PARALLEL, 6-12 calls)        │
│  Runway Gen-3 / Pika 2.0 / Pollinations img2vid            │
│  Each: reference_image → 5-8 second video clip             │
│  Deterministic seeds per scene                              │
└────────┬──────────────────┬──────────────────┬──────────────┘
         │                  │                  │
         ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ VIDEO QC #1     │ │ VIDEO QC #2     │ │ VIDEO QC #N     │
│ Level 2, LLM    │ │ Level 2, LLM    │ │ SWARM: 6-12     │
│ Checks: chars,  │ │ Checks: colors, │ │ PARALLEL        │
│ colors, sig_items│ │ lighting, action│ │                 │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                     │
         │  PASS? ✓          │  FAIL? ✗            │  PASS? ✓
         ▼                   ▼                     ▼
    ┌────────┐          ┌────────┐            ┌────────┐
    │ Store  │          │ Retry  │            │ Store  │
    │ in R2  │          │ (max 2)│            │ in R2  │
    └────────┘          └────────┘            └────────┘
                             │
                             ▼ (still failing after 2 retries)
                        ┌───────────────┐
                        │ DEGRADE:      │
                        │ Static image  │
                        │ + Ken Burns   │
                        │ zoom effect   │
                        └───────────────┘
```

---

## Agent Details

### Video Prompt Crafter (Level 2, per scene, 6-12 parallel)

```
Input per agent:
  - Scene data (summary, location, characters, emotional beat, target duration)
  - Reference images (character portraits for characters in this scene)
  - Visual Bible (color palette, lighting, camera language for this scene)
  - Cinematographer shot list for this scene

Process:
  1. Incorporate reference image URL with "SAME character as reference" instruction
  2. Lock character appearance: eyes, hair, build, scars, signature items
  3. Define camera movement: "slow push-in", "dolly left", "static wide"
  4. Define lighting: key direction, fill ratio, practical sources
  5. Define action: what happens in this 5-8 seconds
  6. Optimize for specific video API format

Output:
  - video_prompt: full text prompt (API-optimized)
  - reference_image_url: character portrait URL
  - expected_duration_s: 5-8
  - transition_in: "crossfade 1.0s"
  - transition_out: "crossfade 1.0s"
  - seed: deterministic from story_hash + scene_index
  - character_anchors: list of MUST-MATCH features for QC

Prompt structure (Runway format):
  "Character is IDENTICAL to reference image [url].
   Appearance LOCK: steel-gray eyes, braided red beard,
   jagged scar left temple. Boar-head hammer visible at belt.
   
   ACTION: Blacksmith strikes glowing star-metal on anvil.
   Sparks erupt in orange cascade. Muscles tense with each strike.
   Sweat glistens on forehead in forge light.
   
   CAMERA: Medium shot, 50mm, slow push-in over 8 seconds.
   LIGHTING: Warm orange forge fire from frame right.
   Deep shadows on character's left side. Smoke haze.
   
   COLOR PALETTE: #2C1810, #D4451A, #000000.
   
   STYLE: Cinematic, photorealistic, 24fps film grain.
   --duration 8s --seed 42"
```

### Video Quality Controller (Level 2, per clip, 6-12 parallel)

```
Input per agent:
  - Video clip URL (from API call)
  - Visual Bible reference (character bible, color palette, shot list)
  - Character anchors (from Prompt Crafter)

Checks:
  1. CHARACTER CHECK:
     ✅ Eye color matches Character Bible? (steel-gray, not blue)
     ✅ Hair matches? (braided red beard, not short brown)
     ✅ Signature item visible? (boar-head hammer at belt)
     ✅ Scar visible? (jagged scar left temple)

  2. COLOR CHECK:
     ✅ Dominant colors within Visual Bible palette?
     ✅ No jarring color jumps from palette?

  3. COMPOSITION CHECK:
     ✅ Camera angle matches shot list?
     ✅ Character framing appropriate?
     ✅ Lighting matches scene mood?

  4. CONTENT CHECK:
     ✅ Action matches scene description?
     ✅ No hallucinated characters/elements?
     ✅ No modern anachronisms?

  5. TECHNICAL CHECK:
     ✅ Clip not corrupted?
     ✅ Duration within expected range?
     ✅ No severe artifacts?

Scoring:
  0.0-0.3 → REJECT (regenerate with modified prompt)
  0.3-0.6 → WARN (accept but flag for review)
  0.6-1.0 → APPROVE

Output:
  - status: "approved" | "rejected" | "warning"
  - score: 0.0-1.0
  - issues: list of specific problems found
  - suggestions: modified prompt if rejected
```

---

## Multi-Provider Video API Client

```python
class VideoProvider(ABC):
    @abstractmethod
    async def generate(
        self, prompt: str, reference_image_url: str,
        duration_s: int, seed: int
    ) -> VideoClip: ...

class RunwayProvider(VideoProvider):
    """Runway Gen-3: Most cinematic, $0.20/clip, 10s max"""
    API_URL = "https://api.runwayml.com/v1"

class PikaProvider(VideoProvider):
    """Pika 2.0: Good quality, $0.10/clip, 8s max"""
    API_URL = "https://api.pika.art/v1"

class PollinationsProvider(VideoProvider):
    """Pollinations img2vid: Free tier, quality varies"""
    API_URL = "https://gen.pollinations.ai/video"

class VideoAPIClient:
    def __init__(self, provider: str = "pollinations"):
        self.provider = self._get_provider(provider)

    async def generate_clips(
        self, prompts: list[VideoPrompt], semaphore: asyncio.Semaphore
    ) -> list[VideoClip]:
        async def generate_one(prompt: VideoPrompt):
            async with semaphore:  # Limit concurrent API calls
                return await self.provider.generate(
                    prompt.text, prompt.reference_image_url,
                    prompt.duration_s, prompt.seed
                )
        return await asyncio.gather(*[generate_one(p) for p in prompts])
```

---

## Degradation Strategy

```
Video generation fails for a scene:
  ↓
Retry 1: Modified prompt (stronger character anchors)
  ↓
Retry 2: Different provider (e.g., Runway → Pika)
  ↓
Still failing:
  ↓
DEGRADE: Use scene keyframe image + Ken Burns effect
  - Slow zoom in/out on static image
  - Crossfade transition still applies
  - Narration audio still plays
  - Film maintains scene count, just static for this scene

Film never breaks — it gracefully degrades.
```

---

## Tasks

| # | Task | Effort | Depends On |
|---|------|--------|-----------|
| 4.1 | Write VideoPromptCrafter prompt | 3h | — |
| 4.2 | Write VideoQC prompt | 3h | — |
| 4.3 | Implement VideoPromptCrafter agent | 2h | 4.1, BaseAgent |
| 4.4 | Implement VideoQC agent | 2h | 4.2, BaseAgent |
| 4.5 | Implement Runway video provider | 3h | Phase 0 |
| 4.6 | Implement Pika video provider | 2h | Phase 0 |
| 4.7 | Implement Pollinations video provider | 2h | Phase 0 |
| 4.8 | Implement VideoAPIClient (provider abstraction) | 2h | 4.5-4.7 |
| 4.9 | Implement VideoLead orchestrator | 3h | 4.3, 4.4, 4.8 |
| 4.10 | Implement degradation (Ken Burns fallback) | 2h | 4.9 |
| 4.11 | Video clip R2 storage + URL generation | 1h | Phase 0 |
| 4.12 | Write unit tests (mock API) | 2h | 4.3, 4.4 |
| 4.13 | Write integration test (full video swarm) | 2h | 4.9 |
| 4.14 | Write degradation test (API failure → fallback) | 1h | 4.10 |

**Total: ~30 hours (Week 9-10)**

---

## Verification Checklist
- [ ] 8-12 video clips generated for 8-12 scene story
- [ ] All clips in parallel: total API time < 60 seconds
- [ ] Character consistency: QC agent > 80% approval rate
- [ ] Signature items visible in all clips
- [ ] Same story_hash → same video clips (deterministic seeds)
- [ ] Cache hit returns existing R2 URLs
- [ ] API failure → Ken Burns fallback works
- [ ] Degraded film still plays all scenes