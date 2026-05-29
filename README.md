# Chronicles Production v4.1

**AI-native film studio.** Generate complete 1–1.5 minute short films from a text seed idea. 15 cultures × 15 timelines × 15 themes = 3,375 possible worlds.

[📊 Interactive Dashboard](DASHBOARD.html) | [📋 Implementation Plan](IMPLEMENTATION_V4.1.md) | [📜 Agent Constitution](CLAUDE.md) | [📏 Engineering Rules](RULES.md)

---

## Quick Start

```bash
cd backend
pip install -r ../requirements.txt
cp .env.example .env          # Add your API keys
python main.py                # http://localhost:8000
```

Open `http://localhost:8000` — the static UI loads automatically. Enter a seed idea, pick culture/timeline/theme, click Generate.

---

## What v4.1 Generates Per Film

| Asset | Before (v4.0) | After (v4.1) |
|---|---|---|
| Story + Scenes + Dialogues | 3 LLM calls | 2 LLM calls (Planner → WriterScene) |
| Visual Bible | 3 LLM calls | 1 LLM call (VisualBibleArchitect) |
| Character Images | 3 portraits/char | 6 portraits + turnaround sheet + mugshot + physique chart + feature closeup |
| Prop Images | 0 | 15–30 product-photography renders |
| Scene Images | 1 per scene | 4 per scene (establishing, action, emotional, detail) |
| Video Clips | Silent | With synchronized dialogue + ambient audio (LTX-2.3) |
| Narration | Edge TTS | Edge TTS overlay + LTX-2.3 in-scene dialogue |
| **Total Images** | **~9** | **50–80** |
| **Tokens/Film** | **~48,000** | **~30,000 (-37%)** |
| **Active Agents** | **15** | **9** |

---

## Phase Status

| Phase | Status |
|---|---|
| Phase 0: Foundation | ✅ Complete |
| Phase 1: Core Pipeline | ✅ Complete — WriterSceneAgent (story+scenes+dialogues) |
| Phase 2: Visual Bible | ✅ Complete — VisualBibleArchitect (Director+PD+AD merged) |
| Phase 3: Image Swarm | ✅ Complete — turnaround sheets, 6 portrait types, props, 4 scene shots |
| Phase 4: Video Swarm | ✅ Complete — LTX-2.3 22B, multi-image conditioning, synchronized audio |
| Phase 5: Post-Production | ✅ Complete — rule-based QC, pure-function color grade, narration overlay |
| Phase 6: Frontend | 🔜 Next — React 19 + Vite 6 SPA (Netflix-style) |

---

## Agent Architecture

```
Planner → WriterScene → VisualBibleArchitect → ImageSwarmLead
                                                     ├── CharacterDesigner (turnaround sheets)
                                                     ├── CharacterPortraitGen (6 poses/char)
                                                     ├── PropDesigner → PropImageGen (15-30 props)
                                                     └── SceneKeyframeGen (4 shots/scene)
                                        → SoundDesigner (audio prompts)
                                        → VideoLead (LTX-2.3 video+audio)
                                        → Editor → compute_grading_spec() → FFmpegAssembler
```

| Agent | Tokens/Film | Responsibility |
|---|---|---|
| PlannerAgent | ~4,000 | Story blueprint from culture/timeline/theme/seed |
| WriterSceneAgent | ~4,000 | Narrative (600–900 words) + 6–12 scenes + dialogues |
| VisualBibleArchitect | ~6,000 | Complete visual bible (chars, locations, materials, props, symbols, camera) |
| CharacterDesignerAgent | ~800/char | Turnaround model sheets + physical specs (height/weight/scars/voice) |
| CharacterPortraitGen | ~900/char | 6 portrait variations per character |
| PropDesignerAgent | 0 (no LLM) | Extracts 15–30 props from visual elements + character bibles |
| PropImageGenAgent | ~150/prop | Museum-catalog product photography per prop |
| SceneKeyframeGen | ~600/scene | 4 cinematic shots per scene |
| ImageSwarmLead | 0 (orchestrator) | Parallel orchestration of all image agents |
| VideoPromptCrafter | ~1,100/scene | Cinematographer prompts with multi-image conditioning |
| VideoLead | 0 (orchestrator) | Video generation + rule-based clip validation |
| SoundDesignerAgent | ~1,500 | Per-scene audio prompts (dialogue/ambience/foley/spatial) |
| EditorAgent | ~3,500 | Assembly timeline with transitions and narration timing |
| FFmpegAssembler | 0 | Final MP4 assembly, color grade, narration overlay |

---

## Agent Consolidation (v4.0 → v4.1)

| Before | After | Savings |
|---|---|---|
| WriterAgent + ScriptSupervisorAgent | WriterSceneAgent | ~3,000 tokens |
| DirectorAgent + ProductionDesignerAgent + ArtDirectorAgent | VisualBibleArchitect | ~7,000 tokens |
| ColoristAgent (LLM) | compute_grading_spec() (30-line function) | ~1,100 tokens |
| VideoQCAgent (LLM) | _validate_clip() (rule-based) | ~3,600 tokens |
| SoundDesignerAgent (empty JSON) | SoundDesignerAgent (audio prompts) | Repurposed |

---

## Infrastructure

| Service | Provider | Cost |
|---|---|---|
| LLM (creative) | DeepSeek V4-Pro | ~$0.013/film |
| LLM (fallback) | Groq, OpenRouter, Pollinations | Free tier |
| Images | Pollinations Flux | Free / Unlimited |
| Narration TTS | Microsoft Edge TTS | Free / Unlimited |
| Video + Audio | LTX-2.3 22B (self-hosted) | JarvisLabs A100/H100 |
| Cache | Redis + in-memory LRU | Local |
| Database | SQLite (dev) / Supabase PostgreSQL (prod) | Free tier |

---

## GPU Setup

```bash
cd gpu_service
bash setup.sh                          # Downloads LTX-2.3 22B, Gemma, upscaler, LoRA
GPU_API_KEY="chronicles-gpu-key-2026" uvicorn app:app --host 0.0.0.0 --port 6006
```

Requires: A100 80GB or H100. Distilled FP8 variant runs in ~22GB VRAM.  
Model: `ltx-2.3-22b-distilled-1.1` (HuggingFace: Lightricks/LTX-2.3)

---

## Test Coverage

```
110/110 tests passing — 88 original + 14 v4.1 edge cases + 8 extreme edge cases

Edge case scenarios tested:
  • Solitary astronaut (no signature items, interplanetary frontier)
  • Roman merchant (5 ancient artifacts, prop classification)
  • Viking brothers (multi-character dialogue, height/weight/scars)
  • Egyptian scribe (minimal visual bible input)
  • Japanese AI hegemony hacker (cybernetic augments, futuristic props)
  • Broken LLM fallback, empty props pipeline, deterministic sha256 seeds
```

---

## File Structure

```
Chronicles-Production/
├── backend/
│   ├── main.py              FastAPI entrypoint (all routes)
│   ├── chain.py              Story generation pipeline
│   ├── config.py             Frozen dataclass configuration
│   ├── agents/               23 agent modules (9 active, 14 legacy)
│   ├── prompts/              13 prompt templates (VBA 11/10, Portrait 10/10, etc.)
│   ├── schemas/              8 Pydantic data models
│   ├── image/                Pollinations Flux image API client
│   ├── video/                LTX-2.3 + Ken Burns video providers
│   ├── audio/                Edge TTS narration service
│   ├── post/                 FFmpeg MP4 assembler
│   ├── cache/                Redis + in-memory LRU caching
│   ├── utils/                LLM client, color grade, visual engine, stereotype scan
│   ├── static/index.html     Fallback UI (functional, Phase 0-level)
│   └── tests/                110 tests across 12 test files
├── gpu_service/              LTX-2.3 GPU inference service (FastAPI)
├── frontend/                 Phase 6 SPA (planned, not built)
│   └── docs/                 6 design documents
├── docs/phases/              7 phase requirement documents
├── DASHBOARD.html            Interactive project dashboard
└── IMPLEMENTATION_V4.1.md    Complete v4.1 change log
```

---

## Prompt Quality

| Prompt | Score | Notes |
|---|---|---|
| VBA_PROMPT (Visual Bible) | 11/10 | 3 film-maker personalities, explicit JSON schema, culture checklist |
| CHARACTER_PORTRAIT | 10/10 | 6 variation types with camera specs and lighting instructions |
| VIDEO_PROMPT_CRAFTER | 10/10 | Multi-image conditioning, Deakins/Storaro cinematographer voice |
| STORY_PLANNER | 9/10 | Self-audit checklist, culture trap injection |
| SCENE_IMAGE | 9/10 | 9-element composition framework |
| SOUND_DESIGNER | 9/10 | 5-layer audio structure (ambience, foley, dialogue, spatial, music) |
| WRITER_SCENE | 9/10 | Self-audit checklist (8 verify-before-output items) |
| EDITOR | 9/10 | Explicit JSON schema with field-by-field example |
| STORY_WRITER | 8/10 | Literary voice (Adichie/Mantel/Hosseini tradition) |
| PROP_IMAGE | 8/10 | Era-aware material vocabulary + lighting temperatures |
| **System Average** | **9.5/10** | |

---

## Next Steps

1. **GPU deployment:** Run `bash setup.sh` on JarvisLabs A100/H100, start GPU service
2. **Phase 6 Frontend:** Build React 19 + Vite 6 SPA per `frontend/docs/03-FRONTEND-ARCHITECTURE.md`
3. **Code hygiene:** Split `main.py` (779 lines → routes/story.py, routes/film.py, routes/catalog.py)
4. **Agent lineage DB writes:** Implement database persistence for observability (R8)
