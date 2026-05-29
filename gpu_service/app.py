"""
GPU Video Generation Service — LTX-2.3
======================================
Runs on JarvisLabs GPU instance (A100, H100). Receives prompts from
Chronicles backend, runs LTX-2.3 22B inference, returns MP4 clips
with synchronized audio. Model stays warm in VRAM — no reload between clips.

Uses TI2VidTwoStagesPipeline from ltx-pipelines package.

Endpoints:
  POST /generate_clip  — Generate video clip from prompt + reference images + audio prompt
  GET  /health         — GPU status, VRAM, model info
"""

import os
import sys
import time
import asyncio
import traceback
import tempfile
from pathlib import Path
from typing import Optional

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

app = FastAPI(title="Chronicles GPU Video Service", version="3.0.0")

# ─── Configuration ──────────────────────────────────────────────

API_KEY = os.environ.get("GPU_API_KEY", "")
LTX_2_DIR = Path(os.environ.get("LTX_2_DIR", os.path.expanduser("~/LTX-2")))

MODEL_WEIGHTS_PATH = os.environ.get("MODEL_WEIGHTS_PATH", "")
GEMMA_ROOT = os.environ.get("GEMMA_ROOT", "")
SPATIAL_UPSAMPLER_PATH = os.environ.get("SPATIAL_UPSAMPLER_PATH", "")
DISTILLED_LORA_PATH = os.environ.get("DISTILLED_LORA_PATH", "")
if not MODEL_WEIGHTS_PATH:
    models_dir = LTX_2_DIR / "models"
    distilled_11 = models_dir / "ltx-2.3-22b-distilled-1.1.safetensors"
    distilled_10 = models_dir / "ltx-2.3-22b-distilled.safetensors"
    dev_path = models_dir / "ltx-2.3-22b-dev.safetensors"
    if distilled_11.exists():
        MODEL_WEIGHTS_PATH = str(distilled_11)
        print(f"[auto-detect] Found distilled 1.1 model: {distilled_11.name}")
    elif distilled_10.exists():
        MODEL_WEIGHTS_PATH = str(distilled_10)
        print(f"[auto-detect] Found distilled model: {distilled_10.name}")
    elif dev_path.exists():
        MODEL_WEIGHTS_PATH = str(dev_path)
        print(f"[auto-detect] Found dev model: {dev_path.name}")
    else:
        print("[auto-detect] No LTX-2.3 model files found at", models_dir)
if not GEMMA_ROOT:
    gemma_dir = LTX_2_DIR / "models" / "gemma-3-12b"
    if gemma_dir.exists():
        GEMMA_ROOT = str(gemma_dir)
if not SPATIAL_UPSAMPLER_PATH:
    up_path = LTX_2_DIR / "models" / "ltx-2.3-spatial-upscaler-x2-1.1.safetensors"
    if up_path.exists():
        SPATIAL_UPSAMPLER_PATH = str(up_path)
if not DISTILLED_LORA_PATH:
    lora_path = LTX_2_DIR / "models" / "ltx-2.3-22b-distilled-lora-384-1.1.safetensors"
    if lora_path.exists():
        DISTILLED_LORA_PATH = str(lora_path)

# ─── Backend ───────────────────────────────────────────────────

pipeline = None
model_ready = False
startup_time = time.time()

# ─── Schemas ──────────────────────────────────────────────────

class ImageRef(BaseModel):
    url: str = Field(..., description="Reference image URL")
    frame_idx: int = Field(default=0, ge=0, le=200)
    strength: float = Field(default=1.0, ge=0.0, le=1.0)


class GenerateClipRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    images: Optional[List[ImageRef]] = None
    audio_prompt: Optional[str] = Field(default=None, max_length=1000)
    generate_audio: bool = Field(default=True)
    seed: int = Field(default=0, ge=0, le=99999)
    duration_s: int = Field(default=8, ge=4, le=20)


# ─── Auth ─────────────────────────────────────────────────────

async def verify_auth(request: Request):
    if not API_KEY:
        return
    key = request.headers.get("X-API-Key", "")
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header")


# ─── Model loading ────────────────────────────────────────────

def _load_ltx2_pipeline():
    import torch
    if not torch.cuda.is_available():
        print("  [ltx2] CUDA not available, skipping")
        return None
    try:
        from ltx_core.loader import LTXV_LORA_COMFY_RENAMING_MAP, LoraPathStrengthAndSDOps
        from ltx_core.components.guiders import MultiModalGuiderParams
        from ltx_core.model.video_vae import TilingConfig
        from ltx_pipelines.ti2vid_two_stages import TI2VidTwoStagesPipeline
        from ltx_pipelines.utils.args import ImageConditioningInput

        distilled_lora = [
            LoraPathStrengthAndSDOps(
                DISTILLED_LORA_PATH, 0.6, LTXV_LORA_COMFY_RENAMING_MAP
            ),
        ]

        print("  [ltx2] Creating TI2VidTwoStagesPipeline...")
        pipe = TI2VidTwoStagesPipeline(
            checkpoint_path=MODEL_WEIGHTS_PATH,
            distilled_lora=distilled_lora,
            spatial_upsampler_path=SPATIAL_UPSAMPLER_PATH,
            gemma_root=GEMMA_ROOT,
            loras=[],
        )
        print("  [ltx2] Pipeline created, model loaded")
        return pipe
    except Exception as e:
        print(f"  [ltx2] FAILED: {e}")
        traceback.print_exc()
        return None


@app.on_event("startup")
async def startup():
    global pipeline, model_ready
    print(f"Model:  {MODEL_WEIGHTS_PATH}")
    print(f"Gemma:  {GEMMA_ROOT}")
    print(f"Upscaler: {SPATIAL_UPSAMPLER_PATH}")

    if not Path(MODEL_WEIGHTS_PATH).exists():
        print("FATAL: LTX-2.3 model weights not found at", MODEL_WEIGHTS_PATH)
        print("  Run: bash setup.sh")
        return
    if not GEMMA_ROOT or not Path(GEMMA_ROOT).exists():
        print("FATAL: Gemma text encoder not found. Run: bash setup.sh")
        return

    try:
        import torch
        if not torch.cuda.is_available():
            print("FATAL: CUDA not available. Did you select PyTorch template?")
            return
        gpu_name = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"GPU: {gpu_name} ({vram:.1f} GB)")
    except ImportError:
        print("FATAL: PyTorch not found. Run: bash setup.sh")
        return

    print("\n--- Loading LTX-2.3 pipeline ---")
    pipeline = _load_ltx2_pipeline()
    if pipeline is None:
        print("FATAL: Failed to load LTX-2.3 pipeline")
        return

    model_ready = True
    print(f"\n=== Service ready ({time.time()-startup_time:.1f}s) ===")
    print(f"  Model: LTX-2.3 22B")
    print(f"  Pipeline: TI2VidTwoStages")
    print()


# ─── Inference ────────────────────────────────────────────────

async def _infer_ltx2(prompt: str, seed: int, num_frames: int,
                     ref_paths: list, audio_prompt: Optional[str] = None) -> bytes:
    from ltx_core.components.guiders import MultiModalGuiderParams
    from ltx_core.model.video_vae import TilingConfig, get_video_chunks_number
    from ltx_pipelines.utils.args import ImageConditioningInput
    from ltx_pipelines.utils.media_io import encode_video

    video_guider_params = MultiModalGuiderParams(
        cfg_scale=3.0,
        stg_scale=1.0,
        rescale_scale=0.7,
        modality_scale=3.0,
        skip_step=0,
        stg_blocks=[29],
    )
    audio_guider_params = MultiModalGuiderParams(
        cfg_scale=7.0,
        stg_scale=1.0,
        rescale_scale=0.7,
        modality_scale=3.0,
        skip_step=0,
        stg_blocks=[29],
    )

    images = []
    for rp in ref_paths:
        images.append(ImageConditioningInput(
            str(rp["path"]), rp.get("frame_idx", 0),
            rp.get("strength", 1.0), 33
        ))

    frame_rate = 25.0
    tiling_config = TilingConfig.default()

    print(f"  [ltx2] Generating {num_frames} frames, {len(images)} ref images, audio={'yes' if audio_prompt else 'no'}")

    combined_prompt = prompt
    if audio_prompt:
        combined_prompt = f"{prompt}\n\n[AUDIO: {audio_prompt}]"

    video, audio = pipeline(
        prompt=combined_prompt,
        negative_prompt="worst quality, low quality, blurry, distorted",
        seed=seed,
        height=512,
        width=768,
        num_frames=num_frames,
        frame_rate=frame_rate,
        num_inference_steps=40,
        video_guider_params=video_guider_params,
        audio_guider_params=audio_guider_params,
        images=images,
        tiling_config=tiling_config,
    )

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        encode_video(
            video=video,
            fps=frame_rate,
            audio=audio,
            output_path=tmp.name,
            video_chunks_number=get_video_chunks_number(num_frames, tiling_config),
        )
        data = Path(tmp.name).read_bytes()
        Path(tmp.name).unlink()

    print(f"  [ltx2] Exported {len(data)} bytes to MP4 (with {'audio' if audio else 'no audio'})")
    return data


@app.post("/generate_clip")
async def generate_clip(request: Request, body: GenerateClipRequest):
    await verify_auth(request)
    if not model_ready:
        raise HTTPException(status_code=503, detail="Model not ready")

    num_frames = max(9, body.duration_s * 8 + 1)
    ref_paths = []

    try:
        if body.images:
            for img in body.images:
                path = await _download_reference(img.url)
                if path:
                    ref_paths.append({
                        "path": path,
                        "frame_idx": img.frame_idx,
                        "strength": img.strength,
                    })

        t0 = time.time()
        print(f"\n--- generate_clip ---")
        print(f"  Prompt: \"{body.prompt[:80]}...\"")
        print(f"  Refs: {len(ref_paths)}, Audio: {bool(body.audio_prompt)}, Seed: {body.seed}")

        mp4_bytes = await _infer_ltx2(
            body.prompt, body.seed, num_frames, ref_paths, body.audio_prompt
        )

        elapsed = time.time() - t0
        print(f"  OK: {len(mp4_bytes)} bytes in {elapsed:.1f}s")
        print()

        return Response(
            content=mp4_bytes, media_type="video/mp4",
            headers={
                "X-Generation-Time-S": f"{elapsed:.1f}",
                "X-Seed": str(body.seed),
                "X-Frames": str(num_frames),
                "X-Backend": "ltx-2.3",
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"  FAILED: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)[:200]}")
    finally:
        for rp in ref_paths:
            p = rp["path"]
            if p and p.parent:
                for f in p.parent.iterdir():
                    f.unlink(missing_ok=True)
                p.parent.rmdir()


async def _download_reference(url: str) -> Optional[Path]:
    try:
        d = Path(tempfile.mkdtemp())
        out = d / "ref.png"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, follow_redirects=True)
            if resp.status_code == 200 and len(resp.content) > 100:
                out.write_bytes(resp.content)
                print(f"  [ref] Downloaded {len(resp.content)} bytes from {url[:50]}...")
                return out
            print(f"  [ref] Bad response {resp.status_code} from {url[:50]}...")
    except Exception as e:
        print(f"  [ref] Download failed: {e}")
    return None


# ─── Health ───────────────────────────────────────────────────

@app.get("/health")
async def health():
    gpu_info = {"available": False}
    try:
        import torch
        if torch.cuda.is_available():
            reserved = torch.cuda.memory_reserved(0) / 1e9
            total = torch.cuda.get_device_properties(0).total_memory / 1e9
            gpu_info = {
                "available": True,
                "name": torch.cuda.get_device_name(0),
                "vram_free_gb": round(total - reserved, 1),
                "vram_total_gb": round(total, 1),
            }
    except ImportError:
        pass

    return {
        "status": "ok" if model_ready else "degraded",
        "model": "LTX-2.3 22B",
        "model_ready": model_ready,
        "pipeline": "TI2VidTwoStages",
        "uptime_s": round(time.time() - startup_time),
        "gpu": gpu_info,
    }


# ─── Entry point ───────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", "6006"))
    print("=" * 60)
    print(" Chronicles GPU Video Service v3 — LTX-2.3 22B")
    print(" Pipeline: TI2VidTwoStages (video + audio)")
    print(" Port:     %d" % port)
    print(" Auth:     %s" % ("ENABLED" if API_KEY else "DISABLED (insecure)"))
    print("=" * 60)
    uvicorn.run("app:app", host="0.0.0.0", port=port, log_level="info")
