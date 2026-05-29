"""
Chronicles GPU Service — Modal Deployment (LTX-2.3 22B)
=========================================================
Serverless GPU inference for LTX-2.3 audiovisual generation.
Replaces gpu_service/app.py for Modal cloud deployment.

Deploy:
  modal deploy chronicles_modal.py

Setup (one-time):
  1. pip install modal && modal token new
  2. modal volume create ltx2-models
  3. Download models to volume:
     modal volume put ltx2-models ltx-2.3-22b-distilled-1.1.safetensors /models/
     modal volume put ltx2-models ltx-2.3-spatial-upscaler-x2-1.1.safetensors /models/
     modal volume put ltx2-models ltx-2.3-22b-distilled-lora-384-1.1.safetensors /models/
     (Gemma text encoder downloaded automatically on first run)
  4. modal deploy chronicles_modal.py
  5. Set CLOUD_GPU_ENDPOINT to the URL Modal gives you
"""

import os
import time
import tempfile
import traceback
from pathlib import Path
from typing import Optional, List

import modal

# ─── Modal app definition ──────────────────────────────────────────

app = modal.App("chronicles-gpu")

# Persistent volume for model weights (survives cold starts)
MODELS_DIR = Path("/models")

volume = modal.Volume.from_name("ltx2-models", create_if_missing=True)

# Container image with all dependencies
gpu_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ffmpeg", "git", "git-lfs")
    .pip_install(
        "torch>=2.7.0",
        "torchvision>=0.19.0",
        "diffusers>=0.30",
        "transformers>=4.44",
        "accelerate>=0.30",
        "sentencepiece",
        "protobuf>=3.20",
        "tiktoken>=0.5.0",
        "httpx>=0.27",
        "pydantic>=2.0",
        "numpy",
    )
    .run_commands(
        "git clone https://github.com/Lightricks/LTX-2.git /ltx2 --depth 1",
        "cd /ltx2 && pip install -e packages/ltx-core -e packages/ltx-pipelines -q",
    )
)

# ─── GPU function ──────────────────────────────────────────────────

@app.function(
    gpu="H100",
    timeout=600,
    volumes={str(MODELS_DIR): volume},
    image=gpu_image,
    allow_concurrent_inputs=4,
)
@modal.web_endpoint(method="POST", label="generate-clip")
async def generate_clip(request):
    """Generate a video clip with synchronized audio using LTX-2.3."""
    import torch
    from ltx_core.components.guiders import MultiModalGuiderParams
    from ltx_core.loader import LTXV_LORA_COMFY_RENAMING_MAP, LoraPathStrengthAndSDOps
    from ltx_core.model.video_vae import TilingConfig, get_video_chunks_number
    from ltx_pipelines.ti2vid_two_stages import TI2VidTwoStagesPipeline
    from ltx_pipelines.utils.args import ImageConditioningInput
    from ltx_pipelines.utils.media_io import encode_video
    from fastapi import Response, HTTPException

    t0 = time.time()

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    prompt = body.get("prompt", "")
    images_data = body.get("images", [])
    seed = body.get("seed", 0)
    duration_s = body.get("duration_s", 8)

    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt is required")

    # Auto-detect model checkpoint
    checkpoint = None
    for candidate in [
        "ltx-2.3-22b-distilled-1.1.safetensors",
        "ltx-2.3-22b-distilled.safetensors",
        "ltx-2.3-22b-dev.safetensors",
    ]:
        candidate_path = MODELS_DIR / candidate
        if candidate_path.exists():
            checkpoint = str(candidate_path)
            break

    if not checkpoint:
        raise HTTPException(
            status_code=503,
            detail="Model weights not found. Upload to Modal volume: modal volume put ltx2-models <file> /models/",
        )

    upscaler_path = MODELS_DIR / "ltx-2.3-spatial-upscaler-x2-1.1.safetensors"
    if not upscaler_path.exists():
        raise HTTPException(
            status_code=503,
            detail="Spatial upscaler not found. Upload to /models/",
        )

    lora_path = MODELS_DIR / "ltx-2.3-22b-distilled-lora-384-1.1.safetensors"
    if not lora_path.exists():
        raise HTTPException(
            status_code=503,
            detail="Distilled LoRA not found. Upload to /models/",
        )

    # Gemma text encoder — download on first use if not present
    gemma_root = MODELS_DIR / "gemma-3-12b-it-qat-q4_0-unquantized"
    if not gemma_root.exists():
        print(f"[startup] Downloading Gemma text encoder to {gemma_root}...")
        from huggingface_hub import snapshot_download
        snapshot_download(
            "google/gemma-3-12b-it-qat-q4_0-unquantized",
            local_dir=str(gemma_root),
            local_dir_use_symlinks=False,
        )

    # ─── Load pipeline ─────────────────────────────────────────
    print(f"[infer] Loading LTX-2.3 pipeline: {Path(checkpoint).name}")
    distilled_lora = [
        LoraPathStrengthAndSDOps(str(lora_path), 0.6, LTXV_LORA_COMFY_RENAMING_MAP),
    ]

    pipeline = TI2VidTwoStagesPipeline(
        checkpoint_path=checkpoint,
        distilled_lora=distilled_lora,
        spatial_upsampler_path=str(upscaler_path),
        gemma_root=str(gemma_root),
        loras=[],
    )

    # ─── Download reference images ─────────────────────────────
    import httpx
    from urllib.parse import urlparse

    ref_image_paths = []
    async with httpx.AsyncClient(timeout=30) as client:
        for img in images_data:
            url = img.get("url", "")
            if not url:
                continue
            try:
                resp = await client.get(url, follow_redirects=True)
                if resp.status_code == 200 and len(resp.content) > 100:
                    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                    tmp.write(resp.content)
                    tmp.close()
                    ref_image_paths.append({
                        "path": tmp.name,
                        "frame_idx": img.get("frame_idx", 0),
                        "strength": img.get("strength", 1.0),
                    })
            except Exception as e:
                print(f"  [ref] Download failed: {e}")

    # ─── Run inference ─────────────────────────────────────────
    num_frames = max(9, duration_s * 8 + 1)
    frame_rate = 25.0
    tiling_config = TilingConfig.default()

    video_guider = MultiModalGuiderParams(
        cfg_scale=3.0,
        stg_scale=1.0,
        rescale_scale=0.7,
        modality_scale=3.0,
        skip_step=0,
        stg_blocks=[29],
    )
    audio_guider = MultiModalGuiderParams(
        cfg_scale=7.0,
        stg_scale=1.0,
        rescale_scale=0.7,
        modality_scale=3.0,
        skip_step=0,
        stg_blocks=[29],
    )

    images = []
    for rp in ref_image_paths:
        images.append(ImageConditioningInput(
            rp["path"], rp["frame_idx"], rp["strength"], 33
        ))

    print(f"[infer] Generating {num_frames} frames ({duration_s}s), "
          f"{len(images)} ref images, seed={seed}")

    video, audio = pipeline(
        prompt=prompt,
        negative_prompt="worst quality, low quality, blurry, distorted, deformed",
        seed=seed,
        height=512,
        width=768,
        num_frames=num_frames,
        frame_rate=frame_rate,
        num_inference_steps=40,
        video_guider_params=video_guider,
        audio_guider_params=audio_guider,
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
        mp4_bytes = Path(tmp.name).read_bytes()
        Path(tmp.name).unlink()

    # Clean up downloaded reference images
    for rp in ref_image_paths:
        try:
            Path(rp["path"]).unlink(missing_ok=True)
        except Exception:
            pass

    elapsed = time.time() - t0
    print(f"[infer] OK: {len(mp4_bytes)} bytes in {elapsed:.1f}s")

    return Response(
        content=mp4_bytes,
        media_type="video/mp4",
        headers={
            "X-Generation-Time-S": f"{elapsed:.1f}",
            "X-Seed": str(seed),
            "X-Frames": str(num_frames),
            "X-Backend": "ltx-2.3-modal",
        },
    )


# ─── Health endpoint ─────────────────────────────────────────────

@app.function(image=gpu_image)
@modal.web_endpoint(method="GET", label="health")
async def health():
    info = {"status": "ok", "model": "LTX-2.3 22B", "pipeline": "TI2VidTwoStages"}
    if MODELS_DIR.exists():
        models = [f.name for f in MODELS_DIR.iterdir() if f.suffix == ".safetensors"]
        info["models_available"] = models
    return info
