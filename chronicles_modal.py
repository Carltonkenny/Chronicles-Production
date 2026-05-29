"""
Chronicles GPU Service — Modal Deployment (LTX-2.3 22B)
=========================================================
Serverless GPU inference for LTX-2.3 audiovisual generation.

QUICK START:
  1. pip install modal && modal token new
  2. modal volume create ltx2-models
  3. modal run chronicles_modal.py::setup          ← downloads models to volume (CPU, free)
  4. modal deploy chronicles_modal.py               ← deploys GPU endpoint
  5. Set CLOUD_GPU_ENDPOINT in backend/.env to the URL from step 4

ARCHITECTURE:
  setup()       → runs on CPU (free download time, no GPU cost)
  generate_clip → runs on H100 GPU (billable only during inference)
  health()      → runs on CPU

MODELS (auto-downloaded by setup):
  - LTX-2.3 22B distilled 1.1 (~42GB)
  - Spatial upscaler x2
  - Distilled LoRA 384 1.1
  - Gemma 3 12B text encoder
"""

from pathlib import Path
from typing import Optional, List

import modal

# ─── Constants ─────────────────────────────────────────────────────

MODELS_DIR = Path("/models")

HUGGINGFACE_REPO = "Lightricks/LTX-2.3"

MODEL_FILES = [
    "ltx-2.3-22b-distilled-1.1.safetensors",
    "ltx-2.3-spatial-upscaler-x2-1.1.safetensors",
    "ltx-2.3-22b-distilled-lora-384-1.1.safetensors",
]

GEMMA_REPO = "google/gemma-3-12b-it-qat-q4_0-unquantized"
GEMMA_DIR = MODELS_DIR / "gemma-3-12b-it-qat-q4_0-unquantized"

ALL_FILES_TEXT = ", ".join(MODEL_FILES) + f", {GEMMA_REPO}"

# ─── Modal app ─────────────────────────────────────────────────────

app = modal.App("chronicles-gpu")

volume = modal.Volume.from_name("ltx2-models", create_if_missing=True)

# ─── Images ────────────────────────────────────────────────────────

# CPU image for setup (no GPU needed for downloads)
setup_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("huggingface_hub[hf_transfer]>=0.28")
)

# GPU image for inference
gpu_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ffmpeg", "git", "git-lfs")
    .pip_install(
        "torch>=2.7.0",
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


# ═══════════════════════════════════════════════════════════════════
# SETUP — Download models to Volume (CPU, FREE)
# ═══════════════════════════════════════════════════════════════════

@app.function(
    cpu=4.0,
    memory=8192,
    timeout=3600,
    volumes={str(MODELS_DIR): volume},
    image=setup_image,
)
def setup():
    """
    Download all LTX-2.3 model weights to the Modal Volume.
    Runs on CPU — no GPU cost. One-time operation.

    Usage: modal run chronicles_modal.py::setup
    """
    import time as _time
    from huggingface_hub import hf_hub_download, snapshot_download

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    t_start = _time.time()

    # ─── Download LTX-2.3 model files ─────────────────────────────
    for idx, filename in enumerate(MODEL_FILES, 1):
        dest = MODELS_DIR / filename
        if dest.exists():
            size_gb = dest.stat().st_size / 1e9
            print(f"[{idx}/4] SKIP {filename} ({size_gb:.1f} GB, already exists)")
            continue

        print(f"[{idx}/4] DOWNLOAD {filename}...")
        _t = _time.time()
        path = hf_hub_download(
            HUGGINGFACE_REPO,
            filename,
            local_dir=str(MODELS_DIR),
            local_dir_use_symlinks=False,
        )
        size_gb = Path(path).stat().st_size / 1e9
        print(f"  OK: {size_gb:.1f} GB in {_time.time() - _t:.0f}s")

    # ─── Download Gemma text encoder ──────────────────────────────
    if GEMMA_DIR.exists() and any(GEMMA_DIR.iterdir()):
        print("[4/4] SKIP Gemma text encoder (already downloaded)")
    else:
        print("[4/4] DOWNLOAD Gemma text encoder (may take 10-15 min)...")
        _t = _time.time()
        snapshot_download(
            GEMMA_REPO,
            local_dir=str(GEMMA_DIR),
            local_dir_use_symlinks=False,
        )
        file_count = sum(1 for _ in GEMMA_DIR.rglob("*") if _.is_file())
        print(f"  OK: {file_count} files in {_time.time() - _t:.0f}s")

    elapsed = _time.time() - t_start
    print(f"\n=== SETUP COMPLETE in {elapsed:.0f}s ({elapsed/60:.0f} min) ===")

    # ─── Verify ───────────────────────────────────────────────────
    print("\nVerification:")
    all_ok = True
    for filename in MODEL_FILES:
        dest = MODELS_DIR / filename
        ok = dest.exists()
        print(f"  {'OK' if ok else 'MISSING'}: {filename}")
        if not ok:
            all_ok = False
    ok = GEMMA_DIR.exists()
    print(f"  {'OK' if ok else 'MISSING'}: {GEMMA_DIR.name}")
    if not ok:
        all_ok = False

    if all_ok:
        print(f"\nALL MODELS READY. Deploy now: modal deploy chronicles_modal.py")
    else:
        print("\nSOME MODELS MISSING. Re-run: modal run chronicles_modal.py::setup")
        raise SystemExit(1)


# ═══════════════════════════════════════════════════════════════════
# GENERATE CLIP — GPU inference (H100, billable)
# ═══════════════════════════════════════════════════════════════════

def _load_pipeline():
    """Load LTX-2.3 pipeline. Cached globally in container memory."""
    import torch
    from ltx_core.loader import LTXV_LORA_COMFY_RENAMING_MAP, LoraPathStrengthAndSDOps
    from ltx_pipelines.ti2vid_two_stages import TI2VidTwoStagesPipeline

    # Auto-detect checkpoint
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
        raise RuntimeError(
            "No LTX-2.3 model found in /models. "
            "Run: modal run chronicles_modal.py::setup"
        )

    upscaler = MODELS_DIR / "ltx-2.3-spatial-upscaler-x2-1.1.safetensors"
    lora = MODELS_DIR / "ltx-2.3-22b-distilled-lora-384-1.1.safetensors"
    gemma = GEMMA_DIR

    for required, label in [(upscaler, "spatial upscaler"), (lora, "distilled LoRA"), (gemma, "Gemma encoder")]:
        if not required.exists():
            raise RuntimeError(
                f"{label} not found at {required}. "
                "Run: modal run chronicles_modal.py::setup"
            )

    distilled_lora = [
        LoraPathStrengthAndSDOps(str(lora), 0.6, LTXV_LORA_COMFY_RENAMING_MAP),
    ]

    return TI2VidTwoStagesPipeline(
        checkpoint_path=checkpoint,
        distilled_lora=distilled_lora,
        spatial_upsampler_path=str(upscaler),
        gemma_root=str(gemma),
        loras=[],
    )


@app.function(
    gpu="H100",
    timeout=600,
    volumes={str(MODELS_DIR): volume},
    image=gpu_image,
)
@modal.fastapi_endpoint(method="POST")
async def generate_clip(request):
    """Generate a video clip with synchronized audio using LTX-2.3."""
    import time as _time
    import tempfile
    import traceback
    import httpx
    from pathlib import Path
    from fastapi import Response, HTTPException

    from ltx_core.components.guiders import MultiModalGuiderParams
    from ltx_core.model.video_vae import TilingConfig, get_video_chunks_number
    from ltx_pipelines.utils.args import ImageConditioningInput
    from ltx_pipelines.utils.media_io import encode_video

    t0 = _time.time()

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

    # ─── Load pipeline ─────────────────────────────────────────
    t_load = _time.time()
    try:
        pipeline = _load_pipeline()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    print(f"[infer] Pipeline loaded in {_time.time() - t_load:.1f}s")

    # ─── Download reference images ─────────────────────────────
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
                print(f"  [ref] download failed for {url[:60]}: {e}")

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

    print(f"[infer] {num_frames} frames ({duration_s}s), "
          f"{len(images)} refs, seed={seed}")

    t_infer = _time.time()
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
    print(f"[infer] Denoised in {_time.time() - t_infer:.1f}s")

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

    # Clean up ref images
    for rp in ref_image_paths:
        try:
            Path(rp["path"]).unlink(missing_ok=True)
        except Exception:
            pass

    elapsed = _time.time() - t0
    size_mb = len(mp4_bytes) / 1e6
    print(f"[infer] OK: {size_mb:.1f} MB in {elapsed:.1f}s")

    return Response(
        content=mp4_bytes,
        media_type="video/mp4",
        headers={
            "X-Generation-Time-S": f"{elapsed:.1f}",
            "X-Seed": str(seed),
            "X-Frames": str(num_frames),
            "X-Backend": "ltx-2.3-modal-h100",
        },
    )


# ═══════════════════════════════════════════════════════════════════
# HEALTH — Status check (CPU, free)
# ═══════════════════════════════════════════════════════════════════

@app.function(image=gpu_image)
@modal.fastapi_endpoint(method="GET")
async def health():
    info = {
        "status": "ok",
        "model": "LTX-2.3 22B",
        "pipeline": "TI2VidTwoStages",
        "models_dir": str(MODELS_DIR),
    }
    if MODELS_DIR.exists():
        found = [f.name for f in MODELS_DIR.iterdir()
                 if f.suffix in (".safetensors",) or f.is_dir()]
        info["models_present"] = found
        expected = MODEL_FILES + ["gemma-3-12b-it-qat-q4_0-unquantized"]
        info["all_models_ready"] = all(
            (MODELS_DIR / e).exists() for e in expected
        )
    return info
