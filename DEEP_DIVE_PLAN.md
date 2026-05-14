# 🎬 Chronicles Production System — Master Architecture Plan

**Version:** 4.0 — Free-Tier Optimized Film Production Swarm  
**Date:** May 2026  
**Status:** Architecture Design Complete

---

## EXECUTIVE SUMMARY

Chronicles Production is an AI-native film studio. You provide a seed idea, a culture, a timeline, and a theme. The system generates a complete 1–1.5 minute short film with:

- Full narrative prose (600–900 words, literary quality)
- 10–15 AI-generated still images (character portraits + scene settings)
- 8–12 AI-generated video clips (stitched into a continuous film)
- Narration audio (Amazon Polly, configurable)
- Background music + ambient sound
- Netflix-style cinematic UI with chapter navigation

**All built to run on free-tier infrastructure, scaling gradually to paid tiers.**

---

## THE 10×10×10 MATRIX (1,000 Combinations)

### CULTURES — 10 Civilization Types

| # | Enum | Display | Narrative DNA |
|---|-------|---------|---------------|
| 1 | `roman` | Imperial Rome | Law, legions, republic-to-autocracy, cursus honorum |
| 2 | `egyptian` | Ancient Egypt | Nile theocracy, ma'at, afterlife civilization, scribal elite |
| 3 | `japanese` | Feudal Japan | Bushido, isolation, zen aesthetic, daimyo rivalry |
| 4 | `viking` | Norse Scandinavia | Thing-democracy, saga tradition, maritime trade, reputation economy |
| 5 | `aztec` | Aztec Triple Alliance | Flower wars, nahualism, chinampas, tribute empire |
| 6 | `mali_empire` | Mali Empire | Gold-salt trade, griot oral tradition, Sankore university |
| 7 | `polynesian` | Polynesian Voyagers | Wayfinding navigation, mana/tapu, star compass |
| 8 | `ottoman` | Ottoman Empire | Millet system, gunpowder empire, three-continent bridge |
| 9 | `nazi_germany` | Third Reich | Totalitarian surveillance, propaganda state, moral descent, resistance |
| 10 | `indian` | Indian Subcontinent | Caste dharma, temple economies, bhakti devotion, nonviolent resistance |

### TIMELINES — 10 Material Eras

| # | Enum | Display | Defining Tech |
|---|-------|---------|---------------|
| 1 | `bronze_age` | Bronze Age | Copper-tin alloying, palace economies, chariots, first writing |
| 2 | `iron_age` | Iron Age | Iron smelting, coinage, alphabet, axial age philosophy |
| 3 | `classical_antiquity` | Classical Antiquity | Roads, standing armies, maritime empires, philosophy |
| 4 | `high_medieval` | High Medieval | 3-field rotation, Gothic, guilds, scholasticism |
| 5 | `early_modern` | Early Modern | Printing press, gunpowder, transoceanic ships |
| 6 | `industrial_revolution` | Industrial Revolution | Steam, factories, railways, class consciousness |
| 7 | `digital_age` | Digital Age | Internet, AI, surveillance capitalism |
| 8 | `post_apocalyptic` | Post-Apocalyptic | Collapse, salvage, neo-tribalism |
| 9 | `ai_hegemony` | AI Hegemony | Autonomous AI, neural interfaces, algorithmic caste |
| 10 | `interplanetary_frontier` | Interplanetary Frontier | Mars colonies, asteroid mining, vacuum survival |

### THEMES — 10 Emotional Arcs

| # | Enum | Story Shape |
|---|-------|-------------|
| 1 | `ambition` | Rise → cost → reckoning |
| 2 | `betrayal` | Trust → fracture → consequence |
| 3 | `redemption` | Fall → darkness → atonement |
| 4 | `sacrifice` | Choice → loss → earned meaning |
| 5 | `discovery` | Ignorance → search → revelation |
| 6 | `resistance` | Oppression → defiance → cost |
| 7 | `loss` | Attachment → severance → aftermath |
| 8 | `legacy` | Action → inheritance → meaning |
| 9 | `love` | Vulnerability → connection → test |
| 10 | `freedom` | Chains → break → consequence |

**Total combinations: 10 × 10 × 10 = 1,000 unique story universes.**

---

## SYSTEM ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER REQUEST                                   │
│      seed_idea + culture + timeline + theme + config                     │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     PHASE 1: STORY GENERATION (30-40s)                    │
│                                                                          │
│  PLANNER ──► WRITER ──► SCRIPT SUPERVISOR                               │
│  (1 LLM)     (1 LLM)     (1 LLM)                                         │
│                                                                          │
│  Output: Story Bible JSON (title, setting, characters, narrative,        │
│          scene breakdown, emotional arc per scene)                        │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     PHASE 2: VISUAL BIBLE (15-20s)                        │
│                                                                          │
│  DIRECTOR ──► PRODUCTION DESIGNER ──► ART DIRECTOR                      │
│  (1 LLM)      (1 LLM)                   (1 LLM)                          │
│                                                                          │
│  Output: Visual Bible JSON (color palette, lighting, character bibles    │
│          with signature items, architecture, props, camera language)      │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  PHASE 3: IMAGE GENERATION (PARALLEL, ~30s)               │
│                                                                          │
│  ┌──────────────────────┐    ┌──────────────────────┐                    │
│  │ CHAR PORTRAIT SWARM  │    │ SCENE SETTING SWARM  │                    │
│  │ 4-6 agents (parallel)│    │ 6-10 agents (parallel)│                   │
│  └──────────┬───────────┘    └──────────┬───────────┘                    │
│             │                           │                                │
│             └───────────┬───────────────┘                                │
│                         ▼                                                │
│              Pollinations Image API (Flux, free tier)                    │
│                                                                          │
│  Output: 10-15 AI images (character portraits + scene keyframes)         │
│  These images serve as REFERENCE FRAMES for video generation             │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  PHASE 4: VIDEO GENERATION SWARM (PARALLEL, ~60s)         │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │              VIDEO PROMPT CRAFTERS (per scene, 6-12 PARALLEL)     │   │
│  │                                                                   │   │
│  │  Each agent receives:                                             │   │
│  │  - Scene text from Script Supervisor                              │   │
│  │  - Reference image (from Phase 3)                                 │   │
│  │  - Character Bible entries for characters in this scene           │   │
│  │  - Visual Bible (color, lighting, architecture)                   │   │
│  │  - Cinematographer shot list for this scene                       │   │
│  │                                                                   │   │
│  │  Each agent outputs:                                              │   │
│  │  - Optimized video prompt (API-specific)                          │   │
│  │  - Character consistency anchors (signature items)                │   │
│  │  - Transition style IN/OUT                                        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                         │                                                │
│                         ▼                                                │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │              VIDEO API CALLS (6-12 PARALLEL)                      │   │
│  │                                                                   │   │
│  │  Each call: scene reference image → 5-8 second video clip         │   │
│  │  Total: 8-12 clips → 40-96 seconds → 1-1.5 minute film           │   │
│  │  API: Pollinations img2vid / Runway free / Pika free              │   │
│  │  COST: Free tier (limited generations/day)                        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                         │                                                │
│                         ▼                                                │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │              VIDEO QUALITY CONTROLLERS (per clip, 6-12 PARALLEL)  │   │
│  │                                                                   │   │
│  │  Checks per clip:                                                 │   │
│  │  ✅ Character signature items visible?                            │   │
│  │  ✅ Color palette matches Visual Bible?                           │   │
│  │  ✅ Camera language matches shot list?                            │   │
│  │  ✅ No hallucinated elements?                                     │   │
│  │                                                                   │   │
│  │  FAIL → regenerate (max 2 retries)                                │   │
│  │  PASS → mark approved, queue for assembly                         │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  PHASE 5: POST-PRODUCTION (~30s)                          │
│                                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │ EDITOR   │  │ SOUND    │  │ COLORIST │  │ QA       │                 │
│  │ (1 LLM)  │  │ DESIGNER │  │ (1 LLM)  │  │ SUPERVSR │                 │
│  │          │  │ (1 LLM)  │  │          │  │ (1 LLM)  │                 │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘                 │
│       │             │             │             │                        │
│       └─────────────┼─────────────┼─────────────┘                        │
│                     │             │                                      │
│                     ▼             ▼                                      │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │              FINAL ASSEMBLY (FFmpeg)                              │   │
│  │                                                                   │   │
│  │  1. Concatenate video clips (scene order)                         │   │
│  │  2. Add crossfade transitions between scenes                      │   │
│  │  3. Overlay narration audio track (Amazon Polly)                  │   │
│  │  4. Add background music track (Suno/Udio free tier)              │   │
│  │  5. Add ambient sound effects (generated or library)              │   │
│  │  6. Apply color grading LUT (consistent across all scenes)        │   │
│  │  7. Add title card + credits overlay                              │   │
│  │  8. Encode to MP4 (H.264, 1080p)                                  │   │
│  │                                                                   │   │
│  │  Output: chronicles_{story_hash}.mp4 (1-1.5 min, 1080p)          │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   NETFLIX-STYLE FRONTEND (Vanilla JS SPA)                 │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐                  │   │
│  │  │LANDING │ │ FORGE  │ │LIBRARY │ │ PROFILE  │                  │   │
│  │  │(Hero)  │ │(Create)│ │(Browse)│ │(Settings)│                  │   │
│  │  └────────┘ └────────┘ └────────┘ └──────────┘                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     VIEWER EXPERIENCE                              │   │
│  │                                                                   │   │
│  │  - Cinematic title card with entry animation                      │   │
│  │  - Chapter/scene selector (click to jump to scene)                │   │
│  │  - Interactive timeline scrubber                                  │   │
│  │  - Character gallery with bios + portraits                        │   │
│  │  - "Behind the Scenes" showing agent lineage                      │   │
│  │  - Narration on/off toggle                                       │   │
│  │  - Fullscreen cinema mode                                         │   │
│  │  - Story text panel (sync-scrolls with video)                     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## AGENT HIERARCHY & AUTHORITY LEVELS

```
LEVEL 0: SHOWRUNNER (1 agent)
│   Ultimate orchestrator. Approves/rejects all department output.
│   Spawns/kills agents. Manages retry budget. Reports film status.
│   Owns story_hash, visual_bible_hash, and film_config.
│   NEVER does creative work — only coordination.
│
├── LEVEL 1: DEPARTMENT HEADS (7 agents)
│   │   DIRECTOR · DP (Cinematography) · CHARACTER LEAD
│   │   VIDEO LEAD · EDITOR · SOUND DESIGNER · QA SUPERVISOR
│   │
│   │   Each Department Head:
│   │   - Receives work order from Showrunner
│   │   - Spawns Level 2 worker agents
│   │   - Collects and validates worker results
│   │   - Can reject and request regeneration (max 2)
│   │   - Reports final department output to Showrunner
│   │
│   ├── LEVEL 2: WORKER SWARMS (15-25 agents, HIGHLY PARALLEL)
│   │   │
│   │   ├── CHARACTER PORTRAIT GENERATORS (4-6 agents)
│   │   │   Generate detailed visual descriptions per character
│   │   │
│   │   ├── SCENE IMAGE GENERATORS (6-10 agents)
│   │   │   Generate setting keyframes per scene
│   │   │
│   │   ├── VIDEO PROMPT CRAFTERS (6-12 agents)
│   │   │   Convert scene descriptions → video API prompts
│   │   │
│   │   └── VIDEO QUALITY CONTROLLERS (6-12 agents)
│   │       Validate each video clip against Visual Bible
│   │
│   │   Each worker:
│   │   - Receives WORK ORDER JSON with all context
│   │   - Has exactly ONE task
│   │   - Returns result + confidence score (0.0-1.0)
│   │   - Has 30s timeout
│   │   - Can signal failure (triggers respawn)
│   │
│   └── LEVEL 3: SUB-WORKERS (only if needed, 0-6 agents)
│       │   LIGHTING REFINER · TRANSITION DESIGNER · CHARACTER ANCHOR CHECKER
│       │   Only spawned if parent worker's confidence < 0.7
```

### TOTAL AGENT COUNTS PER FILM

| Phase | Level 1 | Level 2 | Level 3 | Total |
|-------|---------|---------|---------|-------|
| Story Generation | 3 (Planner, Writer, Script Sup) | — | — | 3 |
| Visual Bible | 3 (Director, Prod Designer, Art Director) | — | — | 3 |
| Image Generation | 1 (Character Lead) | 10-16 (portraits + scenes) | — | 11-17 |
| Video Generation | 1 (Video Lead) | 12-24 (crafters + QC) | 0-6 | 13-31 |
| Post-Production | 3 (Editor, Sound, Colorist) | — | — | 3 |
| QA | 1 (QA Supervisor) | — | — | 1 |
| Showrunner | 1 | — | — | 1 |
| **TOTAL** | **13** | **22-40** | **0-6** | **35-52** |

**Parallel LLM calls: 22-40 (max concurrent), Semaphore-limited to 8-10 for free tier.**

---

## REFERENCE IMAGE STRATEGY (Character Consistency)

The key innovation for video character consistency:

```
Phase 3: Character Portrait → Phase 4: Reference Image for Video
     │                                    │
     │  "Ragnar, steel-gray eyes,         │  Video prompt includes:
     │   jagged scar left temple,         │  "Same character as
     │   wolf-pommel sword,               │   reference image,
     │   brown leather tunic"             │   steel-gray eyes MUST
     │                                    │   match, jagged scar
     └──────── reference image ───────────┘   visible on left temple"
```

Each video prompt includes:
1. **Reference image URL** (character portrait from Phase 3)
2. **Character appearance lock** (eyes, hair, build, scars, signature items)
3. **Shot-specific description** (action, lighting, camera angle)

This dramatically improves character consistency across video clips because the video model has a concrete visual reference.

---

## FREE TIER TECHNOLOGY STACK

| Layer | Technology | Free Tier Limit | Notes |
|-------|-----------|----------------|-------|
| **LLM** | OpenRouter (Gemini Flash 2.0, Llama 4) | 200 req/day | Fallback: Pollinations free tier (unlimited, slower) |
| **Images** | Pollinations Image API (Flux) | Unlimited, anonymous | Deterministic seeding for reproducibility |
| **Video** | Pollinations img2vid / Runway Gen-3 free | ~10 vids/day | Per scene: reference image → 5-8s clip |
| **Audio** | Amazon Polly | 5M chars/month | SSML prosody for expressive narration |
| **Music** | Suno AI / Udio | ~10 songs/day free | Generate per emotional beat |
| **SFX** | Freesound.org / generated | Unlimited | Ambient sound per scene |
| **Database** | Supabase | 500MB PostgreSQL | 2 free projects |
| **Storage** | Cloudflare R2 | 10GB free | Video/image CDN |
| **Hosting** | Render / Railway | Free tier (sleeps) | Upgrade when traffic grows |
| **FFmpeg** | Self-hosted (Docker) | Unlimited | Video assembly |
| **Cache** | Redis (Upstash) | 10K commands/day free | LLM response cache |

### Cost Per Film (Free Tier Rates)

| Component | Calls | Cost |
|-----------|-------|------|
| LLM (35-52 calls) | 25-40 (after caching) | $0.00 (free tier) |
| Images (10-15) | 10-15 API calls | $0.00 (Pollinations free) |
| Video (8-12 clips) | 8-12 API calls | $0.00 (free tiers) |
| Audio narration | 1 Polly call | $0.00 (free tier) |
| Music | 2-3 Suno calls | $0.00 (free tier) |
| FFmpeg assembly | Server-side | $0.00 |
| **TOTAL** | | **$0.00** |

---

## WORKFLOW — END TO END

```
User submits:
  seed_idea: "A blacksmith who forges a blade from fallen star metal"
  culture: viking
  timeline: high_medieval
  theme: ambition

────────────────────────────────────────────────────────────
STEP 1: STORY GENERATION (3 LLM calls, ~30s)
────────────────────────────────────────────────────────────

PLANNER (LLM #1)
  Input: seed + culture + timeline + theme + wiki_context + culture_traps
  Output: Blueprint JSON
    title: "The Star Forge"
    protagonist: Bjorn Ironhand, master smith
    want: Forge a weapon worthy of the gods
    wound: Father's dishonorable death
    plot_beats: [discovery, obsession, cost, reckoning]

WRITER (LLM #2)
  Input: Blueprint + wiki_context
  Output: 700-word narrative with sensory detail, poetic prose

SCRIPT SUPERVISOR (LLM #3)
  Input: Full narrative
  Output: Scene Breakdown JSON
    scenes: [
      { id: 1, summary: "Bjorn finds the star-metal in the frozen river",
        characters: ["Bjorn"], location: "Frozen river at dawn",
        emotional_beat: "discovery_wonder", duration: "8s" },
      { id: 2, summary: "Bjorn begins forging in secret, ignoring his family",
        characters: ["Bjorn", "Sigrid (wife)"], location: "Smoke-filled forge",
        emotional_beat: "obsession_rising", duration: "8s" },
      ...
    ]

────────────────────────────────────────────────────────────
STEP 2: VISUAL BIBLE (3 LLM calls, ~20s)
────────────────────────────────────────────────────────────

DIRECTOR (LLM #4)
  Reads story, creates overall vision + Visual Bible JSON:
    - Film tone: Dark, brooding, fire-lit
    - Pacing: Slow build → frantic climax → quiet resolution
    - Signature items: Bjorn's hammer with boar-head pommel

PRODUCTION DESIGNER (LLM #5)
  World-building details:
    - Forge interior: Timber frame, soot-blackened, leather bellows
    - River location: Ice-choked, pine forest, gray sky
    - Color palette: Iron-gray, forge-orange, ice-blue, charcoal-black

ART DIRECTOR (LLM #6)
  Props and motifs:
    - Star-metal: Irregular chunk, dark silver with faint blue luminescence
    - Bjorn's tools: Heavy iron hammer, leather apron, bronze tongs
    - Cultural symbols: Mjolnir pendant, rune-carved doorframe

────────────────────────────────────────────────────────────
STEP 3: IMAGE GENERATION (10-16 parallel Pollinations calls, ~30s)
────────────────────────────────────────────────────────────

CHARACTER PORTRAIT SWARM (4-6 parallel LLM calls)
  Each generates a detailed visual description prompt for Pollinations:
    "Bjorn Ironhand, Norse blacksmith, 40s, steel-gray eyes, braided
     red beard, jagged scar from temple to jaw, muscular build, wearing
     soot-stained leather tunic, boar-head hammer at belt, forge fire
     reflecting in eyes, cinematic lighting from right, shallow depth
     of field, 50mm lens equivalent"

SCENE SETTING SWARM (6-10 parallel LLM calls)
  Each generates a keyframe description for a scene location:
    "Viking forge interior, timber beams blackened by centuries of smoke,
     leather bellows hanging from rafters, anvil center frame, star-metal
     glowing with faint blue luminescence on anvil, fire in forge casting
     orange light, deep shadows in corners, smoke haze, cinematic wide shot"

  → 10-15 images generated via Pollinations Flux (free, deterministic seeds)
  → These IMAGES become REFERENCE FRAMES for video generation

────────────────────────────────────────────────────────────
STEP 4: VIDEO GENERATION (12-24 LLM calls + 8-12 API calls, ~60s)
────────────────────────────────────────────────────────────

VIDEO PROMPT CRAFTER SWARM (6-12 parallel LLM calls)
  Each agent crafts a prompt for a specific scene:

  Scene 1: "Frozen river at dawn. Camera starts wide on ice-choked river,
            slowly pushes in on figure kneeling at water's edge. Bjorn
            (REFERENCE: character_portrait_1.jpg, MUST have steel-gray eyes,
            braided red beard, jagged scar visible) discovers glowing
            star-metal embedded in ice. Cinematic lighting: cold blue
            dawn light with warm orange glow from star-metal. 8 seconds.
            Camera: 35mm wide establishing → 85mm close-up on discovery."

VIDEO API CALLS (8-12 parallel)
  Pollinations img2vid or Runway Gen-3:
    Input: reference_image + text_prompt
    Output: 5-8 second video clip per scene

  ➜ Scene 1 clip (8s): Discovery scene
  ➜ Scene 2 clip (8s): Forge obsession
  ➜ Scene 3 clip (8s): Family conflict
  ➜ Scene 4 clip (8s): The forging
  ➜ Scene 5 clip (8s): The test
  ➜ Scene 6 clip (8s): The cost
  ➜ Scene 7 clip (8s): Reckoning
  ➜ Scene 8 clip (8s): Resolution
  ➜ Scene 9 clip (8s): Legacy
  Total: 72 seconds (1:12)

VIDEO QUALITY CONTROLLERS (6-12 parallel LLM calls)
  Each validates its clip:
    - Character eyes match reference image?
    - Signature items visible?
    - Color palette consistent?
    - No hallucinated elements?
  → PASS / FAIL / WARN

────────────────────────────────────────────────────────────
STEP 5: POST-PRODUCTION (~30s)
────────────────────────────────────────────────────────────

EDITOR (LLM #25)
  Creates assembly timeline:
    - Scene order: 1→2→3→4→5→6→7→8→9
    - Transitions: Crossfade between scenes
    - Timing: Align with narration script

SOUND DESIGNER (LLM #26)
  1. Generates narration via Amazon Polly (SSML prosody)
  2. Generates ambient sound per scene (wind, fire, ice crack)
  3. Selects/generates background music (Suno/Udio free tier)

COLORIST (LLM #27)
  Applies consistent look:
    - Desaturated cool tones (ice-blue) for river scenes
    - Warm orange glow for forge scenes
    - Gradual warm→cool transition matching emotional arc

FFMPEG ASSEMBLY
  ffmpeg -f concat → merge scenes → overlay audio → color LUT → encode MP4

────────────────────────────────────────────────────────────
STEP 6: QUALITY ASSURANCE
────────────────────────────────────────────────────────────

QA SUPERVISOR (LLM #28)
  Final pass:
    - Continuity: Character looks same in scene 1, 4, 7?
    - Culture: No stereotype traps triggered?
    - Technical: Audio sync? Scene transitions smooth?
    - Emotional: Arc lands?

  Output: chronicles_a3f2b8c9.mp4 (1:12, 1080p, H.264)
          + story_bible.json
          + visual_bible.json
          + agent_lineage.json (who did what)

────────────────────────────────────────────────────────────
FRONTEND: Netflix-style viewer
────────────────────────────────────────────────────────────

  - Title card entry animation
  - Chapter selector (click to jump to scene 1-9)
  - Interactive timeline scrubber
  - Character gallery (portraits + bios)
  - Story text panel (sync-scrolls with video)
  - Narration toggle
  - Behind-the-scenes agent lineage view
  - Fullscreen cinema mode
```

---

## AGENT COMMUNICATION PROTOCOL

### Work Order JSON Schema

Every agent receives and returns this format:

```json
{
  "work_order": {
    "id": "uuid",
    "type": "video_prompt_crafter",
    "parent_agent": "video_lead_1",
    "film_id": "story_hash",
    "scene_id": "scene_3",
    "priority": 1,
    "timeout_ms": 30000,
    "max_retries": 2
  },
  "input": {
    "scene": { "id": "scene_3", "summary": "...", "characters": ["Bjorn", "Sigrid"] },
    "visual_bible": { "color_palette": [...], "lighting": {...} },
    "reference_images": ["portrait_bjorn.jpg", "setting_forge.jpg"],
    "character_bibles": { "Bjorn": { "eyes": "steel-gray", ... } }
  },
  "constraints": {
    "signature_items_required": ["boar_head_hammer", "jagged_scar"],
    "color_palette_locked": true,
    "camera_angle": "35mm wide establishing"
  }
}
```

### Agent Result Schema

```json
{
  "work_order_id": "uuid",
  "agent_id": "video_prompt_crafter_7",
  "status": "completed",
  "confidence": 0.85,
  "output": {
    "video_prompt": "...",
    "transition_in": "crossfade_1s",
    "transition_out": "crossfade_1s",
    "expected_duration_s": 8,
    "seed": 42
  },
  "performance": {
    "llm_calls": 1,
    "tokens_used": 450,
    "wall_time_ms": 3200
  }
}
```

---

## CACHING STRATEGY (Critical for Free Tier)

### What Gets Cached

| Cache Key | Value | TTL |
|-----------|-------|-----|
| `culture|timeline|theme|seed_idea` | Story Bible (Planner + Writer) | 30 days |
| `culture|timeline|theme` | Visual Bible (Director + PD + AD) | 30 days |
| `character_hash|culture` | Character Portrait prompts | Permanent |
| `scene_hash|setting` | Scene Image prompts | Permanent |
| `video_prompt|seed` | Video clip URL | 7 days |
| `narration_hash` | Audio file URL | Permanent |

### Cache Hit Flow

```
1. User submits request
2. Compute story_hash = SHA256(culture|timeline|theme|seed_idea)
3. Check cache:
   - Story hit? → Skip Planner + Writer
   - Visual Bible hit? → Skip Director + PD + AD
   - Image hit? → Skip image generation
   - Video hit? → Return existing video
4. Generate only what's missing
5. Store all results in cache
```

Same seed_idea + same culture + same timeline + same theme = **exact same film, every time, instantly cached.**

---

## DATABASE SCHEMA (Supabase PostgreSQL)

```sql
-- Cultures (10 rows, manually seeded)
CREATE TABLE cultures (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  fallback_text TEXT NOT NULL,  -- 4 paragraphs, human-written
  traps JSONB DEFAULT '[]',     -- ["stereotype_1", "stereotype_2"]
  redirects JSONB DEFAULT '[]', -- ["redirect_1", "redirect_2"]
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Timelines (10 rows, manually seeded)
CREATE TABLE timelines (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  fallback_text TEXT NOT NULL,
  era_dates TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Themes (10 rows, manually seeded)
CREATE TABLE themes (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  craft_notes TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Visual Elements (100 rows: 10 cultures × 10 timelines)
CREATE TABLE visual_elements (
  id SERIAL PRIMARY KEY,
  culture TEXT NOT NULL REFERENCES cultures(id),
  timeline TEXT NOT NULL REFERENCES timelines(id),
  category TEXT NOT NULL,  -- clothing, architecture, artifact, lighting, hairstyle, color_palette
  name TEXT NOT NULL,
  description TEXT,
  materials JSONB DEFAULT '[]',
  colors JSONB DEFAULT '[]',
  UNIQUE(culture, timeline, category, name)
);

-- Story Bibles (every generated story)
CREATE TABLE story_bibles (
  hash TEXT PRIMARY KEY,  -- SHA256 of culture|timeline|theme|seed_idea
  culture_id TEXT NOT NULL,
  timeline_id TEXT NOT NULL,
  theme_id TEXT NOT NULL,
  seed_idea TEXT NOT NULL,
  blueprint_json JSONB,
  story_json JSONB,
  scene_breakdown JSONB,
  stereotypes_flagged JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Visual Bibles (per culture×timeline×theme combo)
CREATE TABLE visual_bibles (
  hash TEXT PRIMARY KEY,  -- SHA256 of culture|timeline|theme
  culture_id TEXT NOT NULL,
  timeline_id TEXT NOT NULL,
  theme_id TEXT NOT NULL,
  bible_json JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Films (final output records)
CREATE TABLE films (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  story_hash TEXT NOT NULL REFERENCES story_bibles(hash),
  visual_bible_hash TEXT REFERENCES visual_bibles(hash),
  video_url TEXT NOT NULL,
  thumbnail_url TEXT,
  duration_seconds INTEGER,
  scene_count INTEGER,
  agent_count INTEGER,
  total_cost_cents INTEGER DEFAULT 0,
  status TEXT DEFAULT 'processing',  -- processing, completed, failed
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent Lineage (trace every agent's work)
CREATE TABLE agent_lineage (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  film_id UUID REFERENCES films(id),
  agent_type TEXT NOT NULL,  -- planner, writer, director, video_prompt_crafter, etc.
  agent_level INTEGER NOT NULL,  -- 0=Showrunner, 1=Dept Head, 2=Worker, 3=Sub-worker
  parent_agent_id UUID,
  work_order JSONB,
  result JSONB,
  status TEXT,  -- success, failed, retry
  tokens_used INTEGER,
  wall_time_ms INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## FRONTEND — NETFLIX-STYLE UI SPEC

```
┌────────────────────────────────────────────────────────────────┐
│  [Chronicles]  FORGE │ LIBRARY │ PROFILE            [🔔] [👤] │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                                                          │  │
│  │              ╔══════════════════════════╗                │  │
│  │              ║   THE STAR FORGE         ║                │  │
│  │              ║   A Viking Story         ║                │  │
│  │              ╚══════════════════════════╝                │  │
│  │                                                          │  │
│  │              ▶ PLAY  │  ⓘ More Info                       │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  CHAPTERS                                                │  │
│  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐       │  │
│  │  │  1  │ │  2  │ │  3  │ │  4  │ │  5  │ │  6  │  ...  │  │
│  │  │ 🧊  │ │ 🔥  │ │ 💔  │ │ ⚒️  │ │ ⚔️  │ │ 🌟  │       │  │
│  │  │Disc │ │Forg │ │Conf │ │The  │ │Test │ │Leg  │       │  │
│  │  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  CHARACTERS                                              │  │
│  │  ┌────────┐  ┌────────┐  ┌────────┐                      │  │
│  │  │ Bjorn  │  │ Sigrid │  │ Olaf   │                      │  │
│  │  │ [PORT] │  │ [PORT] │  │ [PORT] │                      │  │
│  │  │ Smith  │  │ Wife   │  │ Rival  │                      │  │
│  │  └────────┘  └────────┘  └────────┘                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  BEHIND THE SCENES                                       │  │
│  │  Showrunner ─► Director ─► 12 Video Crafters ─► Editor   │  │
│  │  35 agents · $0.00 · 2m 15s render time                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## DEPLOYMENT ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLOUDFLARE                               │
│  R2 (video/images) · Pages (frontend) · Workers (API proxy)     │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────┐
│                        RENDER (Backend)                         │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              FastAPI + Uvicorn (Python 3.12)              │   │
│  │                                                           │   │
│  │  /api/generate-film    — Start film production            │   │
│  │  /api/film/{id}/status — Check progress (SSE)             │   │
│  │  /api/film/{id}        — Get film data + video URL        │   │
│  │  /api/options          — Available cultures/timelines/themes│  │
│  │  /api/library          — Browse completed films           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              BACKGROUND WORKER                            │   │
│  │                                                           │   │
│  │  Showrunner Agent (orchestrates all departments)          │   │
│  │  └─► Department Heads ─► Worker Swarms                   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              FFMPEG Pipeline                               │   │
│  │                                                           │   │
│  │  concat clips → add transitions → overlay audio           │   │
│  │  → color grade → encode MP4 → upload to R2               │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────┐
│                        SUPABASE                                 │
│  PostgreSQL (stories, bibles, films, agent lineage)             │
│  Auth (user accounts, optional)                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## GRADUAL SCALING PLAN

| Tier | Users/Month | Cost/Film | Infrastructure | Revenue |
|------|------------|-----------|----------------|---------|
| **Free (MVP)** | 0-100 | $0.00 | Render free + Supabase free | $0 |
| **Indie** | 100-1K | $0.02 | Render $7/mo + R2 free | $5/film |
| **Creator** | 1K-10K | $0.05 | Render $25/mo + R2 $5 | $2/film |
| **Studio** | 10K+ | $0.15 | Dedicated GPU + CDN | $1/film subscription |

---

## IS THIS REALLY POSSIBLE?

**Yes.** Here's the proof:

1. **Story Generation**: Pollinations AI (gemini-fast) produces 600-900 word culturally-grounded stories. Proven in v1 MVP. The old codebase generated stories successfully.

2. **Image Generation**: Pollinations Flux generates high-quality images from text prompts. Deterministic seeding means same prompt = same image every time. Free, unlimited.

3. **Video Generation**: Runway Gen-3, Pika 2.0, and Pollinations img2vid all produce 4-10 second video clips from image + text input. Multiple companies do this at scale (Synthesia, HeyGen).

4. **Video Assembly**: FFmpeg concatenation + audio overlay + color grading is standard video production. Done billions of times.

5. **Multi-Agent Orchestration**: The pattern of spawning parallel agents, collecting results, and validating is well-established (AutoGen, CrewAI, LangGraph). We're building a domain-specific version for film production.

6. **Netflix-Style UI**: Vanilla JS SPA with video player, chapter navigation, character galleries is standard web development. No framework needed.

**The only question is quality, not feasibility.** Free-tier models produce lower quality than paid. The system degrades gracefully: start free, upgrade as quality demands.

---

## COMPARISON TABLE: MVP vs PRODUCTION

| Dimension | MVP (Nazi folder) | Production v4 |
|-----------|------------------|---------------|
| Cultures | 30 (messy, misclassified) | 10 (clean, distinct types) |
| Timelines | 30 (redundant overlaps) | 10 (full spectrum) |
| Themes | 34 (overlapping arcs) | 10 (structurally distinct) |
| Story Pipeline | Planner → Writer | Planner → Writer → Script Supervisor |
| Visuals | 4 images (1 scene + portraits) | 10-15 images (characters + scene keyframes) |
| Video | None | 8-12 clips, 1-1.5 min film |
| Audio | Polly narration | Polly + Suno music + ambient SFX |
| Agents | 2 | 35-52 (swarm) |
| Consistency | Manual stereotype scan | Signature Items + Video QC swarm |
| Frontend | Basic 4 views | Netflix-style cinematic SPA |
| Database | SQLite (local, in git) | Supabase PostgreSQL (cloud) |
| Observability | Log files | OpenTelemetry + Prometheus |
| Caching | In-memory LRU | Redis + DB persistent |
| Cost | $0.10/story | $0.00/story (free tier) |
| Folder | Nazi/ | Chronicles-Production/ |
