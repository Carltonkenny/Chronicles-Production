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
| Phase 4: Video Swarm | ✅ Complete |
| Phase 5: Post-Production | ✅ Complete |
| Phase 6: Frontend | 🔜 Next |

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
### Phase 4: Video Swarm
✅ VideoPromptCrafter (Deakins/Storaro cinematographer prompts, 6 clips × 10s)
✅ VideoQCAgent (PASS/FAIL/WARN with character anchor validation)
✅ VideoLead orchestrator (parallel crafters → provider → QC → collect)
✅ CloudGPUProvider for self-hosted LTX-Video 13B (JarvisLabs L4, A100)
✅ KenBurnsDegradation fallback (static images + zoom)
✅ GPU service: gpu_service/app.py — FastAPI server running LTX-Video inference
✅ 20 tests (providers, crafters, QC, orchestrator, config)

### Phase 5: Post-Production
✅ Groq LLM provider (llama-3.3-70b creative, llama-3.1-8b for QC/crafters, $0.012/film)
✅ EditorAgent (Schoonmaker/Murch — AssemblyTimeline with transitions, timing)
✅ SoundDesignerAgent (Burtt/Rydstrom — AudioTimeline with narration offsets)
✅ ColoristAgent (Sonnenfeld/Bogdanowicz — film-wide ColorGradingSpec)
✅ FFmpegAssembler (concat, transitions, audio overlay, grading, title card, credits, MP4)
✅ SSE pipeline wired: editing→sound→color→assembly (96%-99% progress)
✅ JSON repair: brace-counting algorithm (no more regex bugs)
✅ /films/{filename} endpoint for serving MP4s
✅ 10 tests (Editor, Sound, Colorist, Assembler)
✅ 88/88 total tests passing

## Infrastructure
✅ Groq LLM (free tier, $0/film)
✅ Pollinations Image API (free, unlimited)
✅ Edge TTS Audio (free, unlimited)
✅ JarvisLabs GPU (L4 spot ₹18/hr, A100 40GB spot ₹74/hr)

## Next Steps

1. Phase 6: Frontend — Netflix-style SPA (Forge, Viewer, Library, Landing)
2. GPU: Deploy and test real L4 video generation with JarvisLabs
3. Phase 5.1: Suno/Udio music integration, Cloudflare R2 storage
