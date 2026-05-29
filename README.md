# Chronicles Production v4.1

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
| Phase 4: Video Swarm | ✅ Complete |
| Phase 5: Post-Production | ✅ Complete |
| Phase 6: Frontend | 🔜 Next |

## Completed Components

### Phase 1: Core Pipeline
✅ 15×15×15 enum system (15 cultures, 15 timelines, 15 themes)
✅ DB fallback data seeded
✅ Force-blending mode detection + counterfactual bridge
✅ Safety constraints (nazi_germany, british_empire, spanish_empire)
✅ Planner → WriterScene pipeline (Writer + ScriptSupervisor merged into one LLM call)
✅ Character dialogues generated per scene (only emotionally significant lines)
✅ Showrunner async generator orchestrator
✅ BaseAgent (timeout, cache, lineage)
✅ LLM client (DeepSeek → Groq → OpenRouter → Pollinations fallback)
✅ Caching (Redis + in-memory LRU)
✅ Stereotype detection + culture traps

### Phase 2: Visual Bible
✅ VisualBibleArchitect — Director + Production Designer + Art Director merged into one LLM call
✅ Visual Bible schema (color palette, lighting, character bibles, props, camera language, cultural symbols, motif arc)
✅ VisualElementsEngine (on-demand generation, anachronism validation, cached 90-day)
✅ Signature items enforced (RULES.md R7)
✅ 15 unit + 8 edge case + 2 pipeline audit tests

### Phase 3: Image Swarm
✅ ImageAPIClient (async Pollinations Flux, deterministic SHA256 seeds, semaphore 8, 1200-char prompts)
✅ CharacterDesignerAgent — turnaround model sheets (front/back/side/action pose, height scale), physical specs
✅ CharacterPortraitGen — 6 variations (full_body, close_up, action, mugshot, physique_chart, feature_closeup)
✅ PropDesignerAgent — extracts all props from visual elements + character bibles (no LLM, pure extraction)
✅ PropImageGenAgent — museum-catalog product photography per prop, culture/timeline-aware
✅ SceneKeyframeGen — 4 shots per scene (establishing, action, emotional, world detail)
✅ ImageSwarmLead — orchestrates CharacterDesigner + Portraits + Props + Scenes in parallel
✅ CHARACTER_QUALITY bug fixed (portraits get portrait-specific quality, not SETTING_QUALITY)

### Phase 4: Video Swarm
✅ GPU service upgraded to LTX-2.3 22B (TI2VidTwoStagesPipeline) — native synchronized audio+video
✅ Multi-image conditioning (4-6 reference images per clip: turnaround sheets + scene images)
✅ Sound Designer repurposed as audio prompt crafter (dialogue, ambience, foley per scene)
✅ Audio prompt merged into video prompt — sent to LTX-2.3 simultaneously
✅ VideoQC replaced by rule-based clip validation (file exists + duration > 0)
✅ KenBurnsDegradation fallback (static images + zoom)
✅ GPU service: gpu_service/app.py v3 — FastAPI server running LTX-2.3 inference

### Phase 5: Post-Production
✅ DeepSeek LLM (V4-Pro for creative, V4-Flash for QC, $0.013/film)
✅ WriterSceneAgent (Story + Scenes + Dialogues in one call)
✅ SoundDesignerAgent — audio prompts for LTX-2.3 (not empty timeline stubs)
✅ Color grading via compute_grading_spec() pure function (eliminated ColoristAgent LLM call)
✅ FFmpegAssembler (concat, transitions, audio overlay, grading, title card, credits, MP4)
✅ SSE pipeline wired through Showrunner
✅ JSON repair: brace-counting algorithm
✅ /films/{filename} endpoint for serving MP4s

## Infrastructure
✅ DeepSeek LLM (V4-Pro for creative, V4-Flash for QC, $0.013/film)
✅ Groq LLM fallback (free tier, no cost)
✅ Pollinations Image API (free, unlimited, 1200-char prompt limit)
✅ Edge TTS Audio (free, unlimited) — narration overlay
✅ LTX-2.3 22B (JarvisLabs A100/H100) — video + synchronized dialogue/ambient audio
✅ GPU service v3 — TI2VidTwoStagesPipeline, multi-image conditioning, audio generation
✅ GPU service auto-heals on resume

## Agent Architecture (v4.1)

| Agent | Role | Tokens |
|-------|------|--------|
| PlannerAgent | Story blueprint | ~4,000 |
| WriterSceneAgent | Narrative + scenes + dialogues (merged from Writer + ScriptSupervisor) | ~4,000 |
| VisualBibleArchitect | Complete visual bible (merged from Director + PD + ArtDirector) | ~6,000 |
| CharacterDesignerAgent | Turnaround sheets + physical specs | ~800/char |
| CharacterPortraitGen | 6 portrait variations per character | ~900/char |
| PropDesignerAgent | Prop extraction (no LLM) | 0 |
| PropImageGenAgent | Per-prop museum catalog images | ~150/prop |
| SceneKeyframeGen | 4 scene shots per scene | ~600/scene |
| ImageSwarmLead | Orchestrator (no LLM) | 0 |
| VideoPromptCrafter | Cinematographer prompts + audio merge | ~1,100/scene |
| VideoLead | Video orchestration + rule-based QC | 0 |
| SoundDesignerAgent | Audio prompts for LTX-2.3 | ~1,500 |
| EditorAgent | Assembly timeline | ~3,500 |
| FFmpegAssembler | Final MP4 assembly | 0 |

**Total: 9 functional agents + 3 orchestrators. ~30,000 tokens/film (was ~48,000).**

## Test Coverage
✅ 102/102 tests passing (88 original + 14 v4.1 edge cases)
✅ Storytelling edge cases: solitary astronaut, Roman merchant, Viking brothers, Egyptian scribe, Japanese AI hegemony

## Next Steps

1. Phase 6: Frontend — Netflix-style SPA (Forge, Viewer, Library, Landing)
2. GPU: Deploy LTX-2.3 22B on JarvisLabs A100/H100, test multi-image + audio
3. Edge TTS narration overlay + LTX-2.3 in-scene dialogue = complete audio pipeline
