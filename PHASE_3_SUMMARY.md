# Phase 3: Image Swarm — Complete

## Status: ✅ COMPLETE | Commit: `69e87b3`

---

## Executive Summary

Phase 3 replaced the monolithic `image_agent.py` (657 lines, sequential execution) with a parallel swarm architecture. Three self-contained BaseAgents — CharacterPortraitGen, SceneKeyframeGen, ImageSwarmLead — generate 10-15 images per film via Pollinations Flux (free, unlimited). Deterministic SHA256 seeds ensure reproducibility. Visual Bible data injected into every prompt for cultural accuracy.

---

## Architecture Decisions

### D1: Swarm Over Monolith

**Why not keep the ported image_agent.py?** At 657 lines, it violated RULES.md CR4 (max 500 lines/file). Sequential generation was slow. Visual Bible data wasn't injected. Each character got a flat keyword-based prompt instead of the detailed character bible data from Phase 2. Splitting into 3 agents per file keeps each under 150 lines.

### D2: 1 LLM Call Per Character (Not Per Variation)

CharacterPortraitGen makes 1 LLM call to generate a detailed visual description, then constructs 3 image URLs (full_body, close_up, action) from that single description. Avoids 3× LLM cost per character. Signature items, color palette, and Visual Bible elements are injected into the prompt.

### D3: 3 Variations Over 4-6

3 portrait variations (full body, close-up, action) plus 1 scene keyframe per scene. Keeps under the semaphore(8) budget with typical 3-5 characters = 9-15 portraits + 6-12 scenes = 15-27 URL constructions, limited to 8 concurrent.

### D4: Empty Data Bug Fixed in main.py

The old `image_agent.generate_all_images()` was called from main.py with empty story_data: `{"setting": "", "story": "", "characters": []}`. The swarm now runs INSIDE the Showrunner orchestrate() method which has actual story data, scenes, and visual bible.

---

## Files Created/Modified

### Created (10 files)

| File | Lines | Purpose |
|------|-------|---------|
| `image/image_api.py` | 154 | Async Pollinations Flux client, deterministic seeds, semaphore |
| `image/__init__.py` | 4 | Package init |
| `schemas/image_result.py` | 22 | ImageResult, ImageOutput Pydantic models |
| `agents/character_portrait_gen.py` | 77 | 1 LLM per character → 3 portrait URLs |
| `agents/scene_keyframe_gen.py` | 52 | 1 LLM per scene → 1 keyframe URL |
| `agents/image_swarm_lead.py` | 147 | Level 1 orchestrator, parallel spawn + collect |
| `prompts/character_portrait_prompt.py` | 53 | LLM prompt with Visual Bible injection |
| `prompts/scene_image_prompt.py` | 36 | LLM prompt for scene keyframes |
| `tests/test_image_swarm.py` | 215 | 26 tests |

### Modified (5 files)

| File | Changes |
|------|---------|
| `agents/__init__.py` | Exported CharacterPortraitGen, SceneKeyframeGen, ImageSwarmLead |
| `schemas/__init__.py` | Exported ImageResult, ImageOutput |
| `agents/showrunner.py` | Wired image_swarm_fn parameter |
| `main.py` | Removed direct image_agent call, wired swarm into SSE |
| `_archived/image_agent.py` | Old 657-line monolith archived |

---

## Test Results

- 26 new tests (schema validation, API client, seed determinism, agents, edge cases)
- 61 total tests passing (35 existing + 26 new)

---

## Rules Compliance

| Rule | Status | Implementation |
|------|--------|---------------|
| R1: Deterministic | ✅ | SHA256(story_hash+suffix) % 9999 seeds |
| R2: Cache First | ✅ | ImageURL construction is deterministic = permanent cache |
| R7: Signature Items | ✅ | Mandatory in CharacterPortraitGen prompt |
| R8: Agent Lineage | ✅ | BaseAgent._write_lineage() |
| WR3: Parallel | ✅ | asyncio.gather in ImageSwarmLead |
| WR4: Semaphore | ✅ | semaphore(8) on ImageAPIClient |
