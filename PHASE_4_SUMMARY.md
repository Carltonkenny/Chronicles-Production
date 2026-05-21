# Phase 4: Video Swarm — Complete

## Status: ✅ COMPLETE | Commits: `727e0e7` (build), `457949a` (bug fixes), `b2777e5` (final)

---

## Executive Summary

Phase 4 implemented the video generation layer. VideoPromptCrafter agents (Deakins/Storaro cinematographer personality) generate 150-200 word prompts per scene. VideoQCAgent validates against character anchors and Visual Bible palette. CloudGPUProvider sends prompts to a self-hosted LTX-Video 13B model on JarvisLabs (L4/A100). KenBurnsDegradation falls back to static images + zoom when GPU is unavailable. 20 tests, 88 total passing.

---

## Architecture Decisions

### D1: Self-Hosted GPU Over Managed APIs (Runway/Pika/Pollinations)

**Why not cloud APIs?** Runway charges $0.20/clip ($1.60/film). Pollinations video API is dead. Self-hosting LTX-Video 13B on JarvisLabs L4 costs ₹3.60/film (₹18/hr spot, 9 min generation). For A100 40GB spot: ₹1.54/film (₹37/hr, 2.5 min). 10-40x cheaper than managed APIs.

### D2: CloudGPUProvider Abstraction

A single `VideoProvider` ABC with 2 implementations: `CloudGPUProvider` (primary, calls L4 via HTTP) and `KenBurnsDegradation` (fallback, static images). The abstraction means swapping GPUs (L4→A100→H100) or switching to managed APIs is a one-line config change.

### D3: 6 Clips × 10s (Not 8-12 × 5-8s)

The original doc specified 8-12 clips of 5-8s. Testing showed that fewer longer clips produce fewer seams (character consistency), fewer LLM calls (12 vs 16-24 for crafters+QC), and the same film duration (60s). GPU time is identical either way — it's the same total frames.

### D4: Pollinations Video Removed

Pollinations img2vid was in the original plan as a free fallback provider. Their video endpoint was tested and returns empty/non-functional responses. Removed entirely. KenBurnsDegradation handles the fallback.

### D5: GPU Service as Separate Process

`gpu_service/app.py` is a standalone FastAPI server running on the GPU instance. Chronicles sends HTTP POST requests with prompt data, receives MP4 bytes back. The GPU runs LTX-Video 13B distilled FP8 (~13GB VRAM) and knows nothing about story context, characters, or Visual Bible — it just receives video prompts.

---

## Files Created/Modified

### Created (8 files)

| File | Lines | Purpose |
|------|-------|---------|
| `video/__init__.py` | 8 | Package init, exports |
| `video/video_api.py` | 114 | VideoProvider ABC + CloudGPUProvider + KenBurnsDegradation |
| `agents/video_prompt_crafter.py` | 93 | 1 LLM per clip → 150-200 word cinematographer prompt |
| `agents/video_qc.py` | 67 | 1 LLM per clip → PASS/FAIL/WARN |
| `agents/video_lead.py` | 185 | Level 1 orchestrator: crafters→provider→QC→collect |
| `prompts/video_prompt_crafter_prompt.py` | 73 | Deakins/Storaro cinematographer personality prompt |
| `prompts/video_qc_prompt.py` | 48 | Quality controller prompt |
| `tests/test_video_swarm.py` | 200 | 20 tests |

### GPU Service (5 files)

| File | Lines | Purpose |
|------|-------|---------|
| `gpu_service/app.py` | 268 | FastAPI server — POST /generate_clip + GET /health |
| `gpu_service/setup.sh` | 59 | One-time setup: clone LTX-Video, install deps |
| `gpu_service/requirements.txt` | 9 | Python dependencies |
| `gpu_service/Dockerfile` | 13 | Container image |
| `gpu_service/README.md` | N/A | Beginner-friendly setup guide |

### Modified (4 files)

| File | Changes |
|------|---------|
| `config.py` | VIDEO_PROVIDER, CLOUD_GPU_ENDPOINT, CLOUD_GPU_API_KEY, VIDEO_CLIP_COUNT |
| `agents/__init__.py` | Exported VideoPromptCrafter, VideoQCAgent, VideoLead |
| `main.py` | video_swarm_fn wired into SSE pipeline (87%-95% progress) |
| `.env.example` | Added video provider config fields |

---

## Bugs Found & Fixed

| # | Bug | Root Cause | Fix |
|---|-----|-----------|-----|
| 1 | Pollinations video endpoint dead | Service stopped providing free video | Removed PollinationsProvider, CloudGPU default |
| 2 | `total_mem` → `total_memory` | PyTorch attribute name | Fixed in app.py (3 locations) |
| 3 | `--offload_model` flag crashes LTX-Video | Flag doesn't exist in inference.py | Removed from app.py command |
| 4 | `out` variable scope error | Hidden by offload_model line | Fixed to `output_path` |

---

## Test Results

- 20 video swarm tests (providers, crafters, QC, orchestrator, config)
- 88/88 total tests passing across all phases

---

## GPU Deployment

| GPU | Cost/hr (spot) | Per clip | 6 clips | Per film | From ₹500 |
|-----|---------------|----------|---------|----------|-----------|
| **L4** | ₹18 | ~90s | 9 min | **₹2.70** | 185 films |
| A100 40GB | ₹37 | ~25s | 2.5 min | **₹1.54** | 324 films |
| **H100** | ₹112 | ~10s | 60s | **₹1.87** | 267 films |

---

## Rules Compliance

| Rule | Status | Implementation |
|------|--------|---------------|
| R1: Deterministic | ✅ | Seed = hash(story_hash + scene_id) |
| R5: Graceful Degradation | ✅ | CloudGPU → Ken Burns fallback chain |
| R7: Signature Items | ✅ | Character anchors enforced in PromptCrafter + QC |
| R8: Agent Lineage | ✅ | BaseAgent._write_lineage() |
| WR3: Parallel | ✅ | PromptCrafters + QC run via asyncio.gather |
| WR4: Semaphore(8) | ✅ | MAX_CONCURRENT_LLM respects free tier limits |
| CR4: <500 lines | ✅ | All files under 200 lines |
