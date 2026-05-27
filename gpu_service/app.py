"""
GPU Video Generation Service
============================
Runs on JarvisLabs GPU instance (L4, A100, H100). Receives prompts from
Chronicles backend, runs LTX-Video 13B inference, returns MP4 clips.
Model stays warm in VRAM — no reload between clips.

Supports 3 inference backends (auto-detected):
  1. diffusers (preferred — official HuggingFace API)
  2. ltx_video.inference (direct package import)
  3. subprocess (fallback — slow but works)

Endpoints:
  POST /generate_clip  — Generate video clip from prompt + optional reference image
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

app = FastAPI(title="Chronicles GPU Video Service", version="2.0.0")

# ─── Configuration ──────────────────────────────────────────────

API_KEY = os.environ.get("GPU_API_KEY", "")
LTX_VIDEO_DIR = Path(os.environ.get("LTX_VIDEO_DIR", os.path.expanduser("~/LTX-Video")))

MODEL_WEIGHTS_PATH = os.environ.get("MODEL_WEIGHTS_PATH", "")
PIPELINE_CONFIG = os.environ.get("PIPELINE_CONFIG", "")
if not MODEL_WEIGHTS_PATH or not PIPELINE_CONFIG:
    models_dir = LTX_VIDEO_DIR / "models"
    fp8_path = models_dir / "ltxv-13b-0.9.8-distilled-fp8.safetensors"
    bf16_path = models_dir / "ltxv-13b-0.9.8-distilled.safetensors"
    if fp8_path.exists():
        if not MODEL_WEIGHTS_PATH:
            MODEL_WEIGHTS_PATH = str(fp8_path)
        if not PIPELINE_CONFIG:
            PIPELINE_CONFIG = "configs/ltxv-13b-0.9.8-distilled-fp8.yaml"
        print(f"[auto-detect] Found FP8 model: {fp8_path.name}")
    elif bf16_path.exists():
        if not MODEL_WEIGHTS_PATH:
            MODEL_WEIGHTS_PATH = str(bf16_path)
        if not PIPELINE_CONFIG:
            PIPELINE_CONFIG = "configs/ltxv-13b-0.9.8-distilled.yaml"
        print(f"[auto-detect] Found BF16 model: {bf16_path.name}")
    else:
        print("[auto-detect] No model files found at", models_dir)
if not PIPELINE_CONFIG:
    PIPELINE_CONFIG = "configs/ltxv-13b-0.9.8-distilled.yaml"

# ─── Backend selection ─────────────────────────────────────────

pipeline = None
inference_py = None
model_ready = False
inference_backend = "none"
startup_time = time.time()

# ─── Schemas ──────────────────────────────────────────────────

class GenerateClipRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500)
    reference_image_url: Optional[str] = None
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

def _try_load_diffusers():
    """Backend 1: Load via HuggingFace diffusers."""
    import torch
    if not torch.cuda.is_available():
        print("  [diffusers] CUDA not available, skipping")
        return None
    try:
        from diffusers import DiffusionPipeline
        print("  [diffusers] Trying from_single_file...")
        pipe = DiffusionPipeline.from_single_file(
            MODEL_WEIGHTS_PATH,
            torch_dtype=torch.bfloat16,
        )
        pipe.to("cuda")
        pipe.enable_model_cpu_offload()
        print("  [diffusers] from_single_file SUCCESS")
        return pipe
    except AttributeError:
        print("  [diffusers] from_single_file not supported (older diffusers), trying from_pretrained...")
        try:
            from diffusers import DiffusionPipeline
            pipe = DiffusionPipeline.from_pretrained(
                "Lightricks/LTX-Video",
                torch_dtype=torch.bfloat16,
                cache_dir=str(LTX_VIDEO_DIR / "hf_cache"),
            )
            pipe.to("cuda")
            print("  [diffusers] from_pretrained SUCCESS")
            return pipe
        except Exception as e2:
            print(f"  [diffusers] from_pretrained FAILED: {e2}")
            traceback.print_exc()
            return None
    except Exception as e:
        print(f"  [diffusers] from_single_file FAILED: {e}")
        traceback.print_exc()
        return None


def _try_load_ltx_direct():
    """Backend 2: Load via ltx_video package directly."""
    import torch
    if not torch.cuda.is_available():
        return None
    try:
        sys.path.insert(0, str(LTX_VIDEO_DIR))
        if (LTX_VIDEO_DIR / "src").exists():
            sys.path.insert(0, str(LTX_VIDEO_DIR / "src"))
        print("  [ltx_direct] Importing ltx_video.inference...")
        import ltx_video.inference as ltx_inf
        print("  [ltx_direct] Creating Pipeline...")
        pipe = ltx_inf.Pipeline(
            model_path=MODEL_WEIGHTS_PATH,
            pipeline_config_path=str(LTX_VIDEO_DIR / PIPELINE_CONFIG),
        )
        print("  [ltx_direct] Loading model into VRAM...")
        pipe.load()
        print("  [ltx_direct] SUCCESS")
        return pipe
    except Exception as e:
        print(f"  [ltx_direct] FAILED: {e}")
        traceback.print_exc()
        return None


@app.on_event("startup")
async def startup():
    global pipeline, inference_py, model_ready, inference_backend
    print(f"Weights: {MODEL_WEIGHTS_PATH}")
    print(f"Config:  {PIPELINE_CONFIG}")

    if not Path(MODEL_WEIGHTS_PATH).exists():
        print("FATAL: Model weights not found at", MODEL_WEIGHTS_PATH)
        print("  Run: bash setup.sh")
        return
    if not LTX_VIDEO_DIR.exists():
        print("FATAL: LTX-Video repo not found at", LTX_VIDEO_DIR)
        print("  Run: bash setup.sh")
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

    # Try backends in order
    print("\n--- Loading inference backend ---")
    pipeline = _try_load_diffusers()
    if pipeline:
        inference_backend = "diffusers"
    else:
        print("\n[diffusers failed, trying ltx_direct...]")
        pipeline = _try_load_ltx_direct()
        if pipeline:
            inference_backend = "ltx_direct"
        else:
            inference_py = LTX_VIDEO_DIR / "inference.py"
            if inference_py.exists():
                inference_backend = "subprocess"
                print(f"\n[Falling back to subprocess: {inference_py}]")
            else:
                print("FATAL: No inference backend available")
                print("  diffusers: failed")
                print("  ltx_direct: failed")
                print("  subprocess: inference.py not found")
                return

    model_ready = True
    print(f"\n=== Service ready ({time.time()-startup_time:.1f}s) ===")
    print(f"  Backend: {inference_backend}")
    print(f"  Pipeline warm: {pipeline is not None}")
    print()


# ─── Inference ────────────────────────────────────────────────

async def _infer_via_pipeline(prompt: str, seed: int, num_frames: int,
                                ref_path: Optional[Path] = None) -> bytes:
    """Use warm pipeline in VRAM (backends 1 or 2)."""
    import torch
    from diffusers.utils import export_to_video

    if inference_backend == "diffusers":
        print("  [infer] Calling diffusers pipeline...")
        result = pipeline(
            prompt=prompt,
            num_frames=num_frames,
            generator=torch.Generator("cuda").manual_seed(seed),
        )
        # Diffusers LTX-Video returns: result.frames = [[PIL, PIL, PIL, ...]]
        frames = result.frames[0]
        print(f"  [infer] Generated {len(frames)} frames via diffusers")
    else:
        kwargs = dict(prompt=prompt, seed=seed, num_frames=num_frames)
        if ref_path:
            kwargs["conditioning_media_paths"] = [str(ref_path)]
            kwargs["conditioning_start_frames"] = [0]
        print("  [infer] Calling ltx_direct pipeline...")
        frames = pipeline(**kwargs)
        print(f"  [infer] Generated {len(frames)} frames via ltx_direct")

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        export_to_video(frames, tmp.name, fps=24)
        data = Path(tmp.name).read_bytes()
        Path(tmp.name).unlink()

    print(f"  [infer] Exported {len(data)} bytes to MP4")
    return data


async def _infer_via_subprocess(prompt: str, seed: int, num_frames: int,
                                  ref_path: Optional[Path] = None) -> bytes:
    """Fallback: spawn subprocess (slow, loads model each time)."""
    import subprocess as sp
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output.mp4"
        cmd = [
            sys.executable, str(inference_py),
            "--pipeline_config", str(LTX_VIDEO_DIR / PIPELINE_CONFIG),
            "--prompt", prompt,
            "--num_frames", str(num_frames),
            "--seed", str(seed),
            "--output_path", str(output_path),
        ]
        if ref_path:
            cmd.extend(["--conditioning_media_paths", str(ref_path)])
            cmd.extend(["--conditioning_start_frames", "0"])

        print(f"  [subprocess] Running: {' '.join(str(c) for c in cmd[:6])}...")
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_data, stderr_data = await asyncio.wait_for(proc.communicate(), timeout=600)
        except asyncio.TimeoutError:
            proc.kill()
            print("  [subprocess] TIMEOUT after 600s")
            raise HTTPException(status_code=504, detail="Inference timed out")

        if proc.returncode != 0:
            err = stderr_data.decode(errors="replace")[-500:] if stderr_data else ""
            print(f"  [subprocess] FAILED (rc={proc.returncode}): {err[:200]}")
            raise HTTPException(status_code=500, detail=f"Inference failed: {err[:200]}")

        data = output_path.read_bytes()
        print(f"  [subprocess] Generated {len(data)} bytes")
        return data


@app.post("/generate_clip")
async def generate_clip(request: Request, body: GenerateClipRequest):
    await verify_auth(request)
    if not model_ready:
        raise HTTPException(status_code=503, detail="Model not ready")

    num_frames = max(9, body.duration_s * 8 + 1)
    ref_path = None

    try:
        if body.reference_image_url:
            ref_path = await _download_reference(body.reference_image_url)

        t0 = time.time()
        print(f"\n--- generate_clip ---")
        print(f"  Prompt: \"{body.prompt[:60]}...\"")
        print(f"  Seed: {body.seed}, Frames: {num_frames}, Backend: {inference_backend}")

        if inference_backend in ("diffusers", "ltx_direct"):
            mp4_bytes = await _infer_via_pipeline(body.prompt, body.seed, num_frames, ref_path)
        else:
            mp4_bytes = await _infer_via_subprocess(body.prompt, body.seed, num_frames, ref_path)

        elapsed = time.time() - t0
        print(f"  ✅ SUCCESS: {len(mp4_bytes)} bytes in {elapsed:.1f}s")
        print()

        return Response(
            content=mp4_bytes, media_type="video/mp4",
            headers={
                "X-Generation-Time-S": f"{elapsed:.1f}",
                "X-Seed": str(body.seed),
                "X-Frames": str(num_frames),
                "X-Backend": inference_backend,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)[:200]}")
    finally:
        if ref_path and ref_path.parent:
            for f in ref_path.parent.iterdir():
                f.unlink(missing_ok=True)
            ref_path.parent.rmdir()


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
        "model_ready": model_ready,
        "backend": inference_backend,
        "pipeline_warm": pipeline is not None,
        "uptime_s": round(time.time() - startup_time),
        "gpu": gpu_info,
    }


# ─── Entry point ───────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", "6006"))
    print("=" * 60)
    print(" Chronicles GPU Video Service v2")
    print(" Model:   warm in VRAM (auto backend detection)")
    print(" Port:    %d" % port)
    print(" Auth:    %s" % ("ENABLED" if API_KEY else "DISABLED (insecure)"))
    print("=" * 60)
    uvicorn.run("app:app", host="0.0.0.0", port=port, log_level="info")
