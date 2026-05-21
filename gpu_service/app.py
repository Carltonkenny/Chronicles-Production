"""
GPU Video Generation Service
============================
Runs on JarvisLabs L4 24GB. Receives prompts from Chronicles backend,
runs LTX-Video 13B inference, returns MP4 clips.

Endpoints:
  POST /generate_clip  — Generate a video clip from prompt + optional reference image
  GET  /health         — GPU status, VRAM, model info
"""

import os
import sys
import io
import time
import hashlib
import json
import asyncio
import tempfile
import subprocess
from pathlib import Path
from typing import Optional

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

app = FastAPI(title="Chronicles GPU Video Service", version="1.0.0")

# ─── Configuration (from environment) ───────────────────────────────

API_KEY = os.environ.get("GPU_API_KEY", "")
LTX_VIDEO_DIR = Path(os.environ.get("LTX_VIDEO_DIR", os.path.expanduser("~/LTX-Video")))
MODEL_WEIGHTS_PATH = Path(os.environ.get(
    "MODEL_WEIGHTS_PATH",
    os.path.expanduser("~/LTX-Video/models/ltxv-13b-0.9.8-distilled-fp8.safetensors")
))
PIPELINE_CONFIG = os.environ.get(
    "PIPELINE_CONFIG",
    "configs/ltxv-13b-0.9.8-distilled-fp8.yaml"
)

# ─── App state ─────────────────────────────────────────────────────

model_ready = False
model_load_time_s = 0.0
startup_time = time.time()
inference_module = None  # Will hold ltx_video.inference if available

# ─── Schemas ───────────────────────────────────────────────────────

class GenerateClipRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500)
    reference_image_url: Optional[str] = Field(default=None)
    seed: int = Field(default=0, ge=0, le=99999)
    duration_s: int = Field(default=8, ge=4, le=20)


# ─── Auth ───────────────────────────────────────────────────────────

async def verify_auth(request: Request):
    if not API_KEY:
        return
    key = request.headers.get("X-API-Key", "")
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header")


# ─── Model loading ─────────────────────────────────────────────────

@app.on_event("startup")
async def load_model():
    global model_ready, model_load_time_s

    print(f"LTX-Video path: {LTX_VIDEO_DIR}")
    print(f"Weights path: {MODEL_WEIGHTS_PATH}")
    print(f"Pipeline config: {PIPELINE_CONFIG}")

    if not LTX_VIDEO_DIR.exists():
        print("LTX-Video repo not found. Run setup.sh first.")
        return
    if not MODEL_WEIGHTS_PATH.exists():
        print("Model weights not found. Run setup.sh first.")
        return

    inference_py = LTX_VIDEO_DIR / "inference.py"
    if not inference_py.exists():
        print(f"inference.py not found at {inference_py}")
        return

    print(f"inference.py found at {inference_py}")

    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            total_vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
            print(f"GPU: {gpu_name} ({total_vram:.1f} GB VRAM)")
            vram_free = (torch.cuda.get_device_properties(0).total_memory -
                         torch.cuda.memory_reserved(0)) / 1024**3
            print(f"VRAM free: {vram_free:.1f} GB")
        else:
            print("WARNING: CUDA not available — inference on CPU will be extremely slow")
    except ImportError:
        print("WARNING: PyTorch not found — install torch>=2.4.0")

    model_load_time_s = time.time() - startup_time
    model_ready = True
    print(f"Service ready ({model_load_time_s:.1f}s to init)")


# ─── Endpoints ─────────────────────────────────────────────────────

@app.get("/health")
async def health():
    gpu_info = {"available": False}
    try:
        import torch
        if torch.cuda.is_available():
            reserved = torch.cuda.memory_reserved(0)
            total = torch.cuda.get_device_properties(0).total_memory
            vram_free = (total - reserved) / 1024**3
            gpu_info = {
                "available": True,
                "name": torch.cuda.get_device_name(0),
                "vram_free_gb": round(vram_free, 1),
                "vram_total_gb": round(total / 1024**3, 1),
            }
    except ImportError:
        pass

    return {
        "status": "ok" if model_ready else "degraded",
        "model": "ltx-13b-0.9.8-distilled-fp8",
        "model_ready": model_ready,
        "init_time_s": round(model_load_time_s, 1),
        "uptime_s": round(time.time() - startup_time),
        "gpu": gpu_info,
        "repo_found": LTX_VIDEO_DIR.exists(),
        "weights_found": MODEL_WEIGHTS_PATH.exists(),
    }


@app.post("/generate_clip")
async def generate_clip(request: Request, body: GenerateClipRequest):
    await verify_auth(request)

    if not model_ready:
        raise HTTPException(status_code=503, detail="Model not ready")
    if not LTX_VIDEO_DIR.exists():
        raise HTTPException(status_code=500,
                            detail=f"LTX-Video repo not at {LTX_VIDEO_DIR}")

    inference_py = LTX_VIDEO_DIR / "inference.py"
    if not inference_py.exists():
        raise HTTPException(status_code=500,
                            detail=f"inference.py not found at {inference_py}")

    ref_path = None
    try:
        if body.reference_image_url:
            ref_path = await _download_reference(body.reference_image_url)

        num_frames = max(9, body.duration_s * 8 + 1)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.mp4"

            cmd = [
                sys.executable,
                str(inference_py),
                "--pipeline_config", str(LTX_VIDEO_DIR / PIPELINE_CONFIG),
                "--prompt", body.prompt,
                "--num_frames", str(num_frames),
                "--seed", str(body.seed),
                "--output_path", str(output_path),
            ]

            if ref_path and ref_path.exists():
                cmd.extend(["--conditioning_media_paths", str(ref_path)])
                cmd.extend(["--conditioning_start_frames", "0"])

            print(f"Inference command: python inference.py --prompt \"{body.prompt[:40]}...\" "
                  f"--num_frames {num_frames} --seed {body.seed}")
            t0 = time.time()

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_data, stderr_data = await asyncio.wait_for(
                    proc.communicate(), timeout=600
                )
            except asyncio.TimeoutError:
                proc.kill()
                raise HTTPException(status_code=504,
                                    detail="Inference timed out after 600s")

            elapsed = time.time() - t0

            if proc.returncode != 0:
                err = stderr_data.decode(errors="replace")[-500:] if stderr_data else ""
                print(f"Inference failed (rc={proc.returncode}): {err}")
                raise HTTPException(status_code=500,
                                    detail=f"Inference failed: {err[:200]}")

            if not output_path.exists() or output_path.stat().st_size == 0:
                raise HTTPException(status_code=500,
                                    detail="Inference produced no output file")

            mp4_bytes = output_path.read_bytes()
            print(f"Generated {len(mp4_bytes)} bytes in {elapsed:.1f}s")

            return Response(
                content=mp4_bytes,
                media_type="video/mp4",
                headers={
                    "X-Generation-Time-S": f"{elapsed:.1f}",
                    "X-Seed": str(body.seed),
                    "X-Frames": str(num_frames),
                }
            )

    finally:
        if ref_path and ref_path.parent:
            try:
                for f in ref_path.parent.iterdir():
                    f.unlink(missing_ok=True)
                ref_path.parent.rmdir()
            except Exception:
                pass


async def _download_reference(url: str) -> Optional[Path]:
    try:
        d = Path(tempfile.mkdtemp())
        out = d / "ref.png"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, follow_redirects=True)
            if resp.status_code == 200 and len(resp.content) > 100:
                out.write_bytes(resp.content)
                print(f"Downloaded reference: {len(resp.content)} bytes")
                return out
    except Exception as e:
        print(f"Download reference failed: {e}")
    return None


# ─── Entry point ───────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print(" Chronicles GPU Video Service")
    print("=" * 60)
    print(f" Model:   LTX-Video 13B distilled FP8")
    print(f" Repo:    {LTX_VIDEO_DIR}")
    print(f" Weights: {MODEL_WEIGHTS_PATH}")
    print(f" Auth:    {'ENABLED' if API_KEY else 'DISABLED (insecure)'}")
    if not API_KEY:
        print(" WARNING: Set GPU_API_KEY env var for production!")
    print()

    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", "6006")), log_level="info")
