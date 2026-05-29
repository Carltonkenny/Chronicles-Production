# IMPLEMENTATION PLAN — Chronicles Production v4.1

## Overview

24 surgical changes across 3 days. Upgrade GPU service to LTX-2.3 22B (native audio+video), expand character/props/scene image generation, consolidate 15 agents → 9. Zero rewrites. ~1,200 lines net changed.

---

## Day 1: GPU Service + Audio Pipeline

### 1. `gpu_service/app.py` — LTX-2.3 upgrade
- Replace model loading: ltxv-13b-0.9.8 → ltx-2.3-22b-distilled-1.1
- Use TI2VidTwoStagesPipeline from ltx-pipelines package
- New endpoint fields: `images: list[ImageConditioningInput]`, `audio_prompt: str`, `generate_audio: bool`
- Output: MP4 with embedded AAC audio track
- Keep: FastAPI structure, /health, error handling, timeout behavior

### 2. `gpu_service/requirements.txt` — Updated dependencies
- Add ltx-core, ltx-pipelines from LTX-2 monorepo
- Remove old ltx_video direct dependencies

### 3. `gpu_service/setup.sh` — New model download
- Update download URLs for LTX-2.3 22B
- Add Gemma 3 text encoder download
- Add spatial upscaler download
- Keep existing GPU detection, env generation

### 4. `backend/video/video_api.py` — Multi-image + audio support
- CloudGPUProvider.generate(): accept list[ImageConditioningInput] + audio_prompt: str
- Request body: {"images": [...], "audio_prompt": "...", "seed": ..., "prompt": "..."}

### 5. `backend/agents/sound_designer.py` — Repurposed as AudioPromptCrafter
- Output changes: audio_timeline → audio_prompts: dict[str, str]
- Maps scene_id → audio prompt string (dialogue direction + ambience + foley + spatial audio)

### 6. `backend/prompts/sound_designer_prompt.py` — Audio prompt template
- New template: takes scenes, characters, visual bible, culture, timeline
- Outputs per-scene audio prompts for direct LTX-2.3 consumption

---

## Day 2: Character + Props + Scene Expansion

### 7. `backend/schemas/image_result.py` — Expanded variation types
- New variations: turnaround_sheet, mugshot, character_sheet, physique_chart, feature_closeup
- New variations: prop_image, environment_asset, establishing_shot, action_shot, emotional_closeup, world_detail, transition_shot
- New models: PropImageResult, expanded ImageOutput with props[] and character_designs[]

### 8. `backend/schemas/props.py` — New PropDetail schema
- name, prop_type (weapon/jewelry/vehicle/tool/furniture/accessory/religious)
- materials, dimensions, colors, era_name, character_owner, scene_used_in, cultural_significance

### 9. `backend/agents/character_designer.py` — Turnaround Sheet Agent
- Receives character bible + culture/timeline/theme
- Outputs turnaround prompt (4-pose single frame with height markers) + physical spec dict
- Story-defined persona flows through (jeweler, playboy, mafia — the story decides)

### 10. `backend/prompts/character_design_prompt.py` — Physical Spec Prompt
- Inputs: character bible, culture, timeline, theme, visual bible color palette
- Output: JSON with physical spec + 200-word turnaround image prompt
- Culture-aware physical traits

### 11. `backend/agents/character_portrait_gen.py` — Expanded variations
- Add mugshot, character_sheet, physique_chart, feature_closeup
- Fix CHARACTER_QUALITY bug (portraits were getting SETTING_QUALITY)

### 12. `backend/agents/prop_designer.py` — Prop Extraction Agent
- Extract props from: visual_elements artifacts, character signature_items, scene materials
- Pure extraction, no LLM

### 13. `backend/agents/prop_image_gen.py` — Prop Image Generator
- Per-prop product-photography style image generation
- Culture/timeline-aware prompts

### 14. `backend/prompts/prop_image_prompt.py` — Prop Image Prompt Template
- Museum catalog product photography style
- Culture-specific material and color guidance

### 15. `backend/agents/scene_keyframe_gen.py` — Multi-shot expansion
- Loop: 1 keyframe → 4 variations per scene (establishing, action, emotional, detail)

### 16. `backend/agents/image_swarm_lead.py` — Expanded orchestration
- Add CharacterDesigner spawns (before CharacterPortraitGen)
- Add PropDesigner + PropImageGen spawns
- SceneKeyframeGen now receives variation_count=4
- All within existing Semaphore throttling

---

## Day 3: Agent Consolidation

### 17. Writer + ScriptSupervisor merge → WriterSceneAgent
- New agent: one LLM call produces {story_data, scenes[], dialogues[]}
- Old files: _archived/writer.py, _archived/script_supervisor.py

### 18. Director + ProductionDesigner + ArtDirector merge → VisualBibleArchitect
- New agent: one LLM call produces complete visual bible
- Visual_engine loaded once (was twice)
- Old files: _archived/director.py, _archived/production_designer.py, _archived/art_director.py

### 19. Colorist → compute_grading_spec() function
- Pure function in utils/color_grade.py (~30 lines)
- Maps palette hex → 5 float FFmpeg values
- Video prompt also embeds grading for LTX-2.3 native handling
- Old file: _archived/colorist.py

### 20. VideoQC → rule-based in VideoLead
- _validate_clip() private method: file exists + duration > 0 + size > minimum
- Old file: _archived/video_qc.py

### 21. VideoPromptCrafter multi-image + audio merge
- Accepts list of images with frame positions
- Merges video prompt + audio prompt → sends combined to LTX-2.3
- Updated prompt template with reference image conditioning section

### 22. `backend/prompts/video_prompt_crafter_prompt.py` — Updated template
- Add reference image conditioning section
- LLM instructed to compose prompts knowing multi-image context

### 23. `backend/agents/showrunner.py` — Orchestration update
- Updated agent sequence: WriterScene → VisualBibleArchitect → ImageSwarm → VideoSwarm → Editor
- Removed: separate Writer, Supervisor, Director, PD, AD, Colorist, VideoQC, SoundDesigner timeline flow

### 24. `backend/config.py` — Constants update
- Add mix_spec constants (DEFAULT_MUSIC_VOLUME_DB, DEFAULT_AMBIENCE_VOLUME_DB, CROSSFADE_DURATION_S)
- Add new agent timeouts
- Add LTX-2.3 GPU endpoint config

---

## Architecture Decision: Sound + Video → Combined Prompt

The SoundDesigner's audio prompt and the VideoPromptCrafter's cinematography prompt are merged into a single prompt sent to LTX-2.3's TI2VidTwoStagesPipeline. LTX-2.3 processes both modalities simultaneously from a unified prompt.

Format:
```
[CINEMATOGRAPHY PROMPT - 150-200 words describing visuals]

[AUDIO PROMPT - 80-100 words describing dialogue, ambience, foley]
```

LTX-2.3 params: video_guider_params.cfg_scale=3.0, audio_guider_params.cfg_scale=7.0, modality_scale=3.0

## Architecture Decision: Multi-Image Conditioning

LTX-2.3 accepts list of ImageConditioningInput(path, frame_idx, strength, crf). Per clip: character turnaround sheet at frame 0, scene establishing shot at frame 0, scene action shot at frame 33, optional prop reference. Practical limit: 4-6 images per clip.

## Agent Count: 15 → 9

| Removed | Action |
|---------|--------|
| ScriptSupervisor | Merged into WriterScene |
| Director | Merged into VisualBibleArchitect |
| ProductionDesigner | Merged into VisualBibleArchitect |
| ArtDirector | Merged into VisualBibleArchitect |
| Colorist | Replaced by pure function |
| VideoQC | Replaced by rule-based check |

| Repurposed | Action |
|------------|--------|
| SoundDesigner | Now generates audio prompts, not empty timeline |

## Files Archived (never deleted)

- agents/writer.py, agents/script_supervisor.py
- agents/director.py, agents/production_designer.py, agents/art_director.py
- agents/colorist.py
- agents/video_qc.py

## Per-Film Output (After)

| Asset | Before | After |
|---|---|---|
| Story docs | 3 LLM calls | 2 LLM calls (Planner + WriterScene) |
| Visual Bible | 3 LLM calls | 1 LLM call (VisualBibleArchitect) |
| Character images | 3 per character | 5-6 per character + 1 turnaround sheet |
| Prop images | 0 | 15-30 per film |
| Scene images | 1 per scene | 4 per scene + transitions |
| Video clips | Silent | With dialogue + ambient audio |
| Tokens per film | ~48,000 | ~30,000 (~37% reduction) |
| Agents (active) | 15 | 9 |
