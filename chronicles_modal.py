"""
Chronicles GPU Server — LTX-2.3 22B on Modal
=============================================
Deploy: modal deploy chronicles_modal.py
Setup first: modal run chronicles_setup.py::setup

Endpoints:
  POST /generate_clip  — Generate video+audio clip
  GET  /health         — Model status
"""

from pathlib import Path

import fastapi
import modal

MODELS_DIR = Path("/models")

MODEL_FILES = [
    "ltx-2.3-22b-distilled-1.1.safetensors",
    "ltx-2.3-spatial-upscaler-x2-1.1.safetensors",
    "ltx-2.3-22b-distilled-lora-384-1.1.safetensors",
]

GEMMA_DIR = MODELS_DIR / "gemma-3-12b-it-qat-q4_0-unquantized"

app = modal.App("chronicles-gpu")
volume = modal.Volume.from_name("ltx2-models", create_if_missing=True)
_PIPELINE = None

gpu_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ffmpeg", "git", "git-lfs")
    .pip_install(
        "fastapi[standard]",
        "torch>=2.7.0",
        "torchvision",
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


def _load_pipeline():
    from ltx_core.loader import LTXV_LORA_COMFY_RENAMING_MAP, LoraPathStrengthAndSDOps
    from ltx_core.quantization.fp8_cast import build_policy as build_fp8_cast_policy
    from ltx_pipelines.ti2vid_two_stages import TI2VidTwoStagesPipeline

    for candidate in ["ltx-2.3-22b-distilled-1.1.safetensors",
                      "ltx-2.3-22b-distilled.safetensors",
                      "ltx-2.3-22b-dev.safetensors"]:
        cp = MODELS_DIR / candidate
        if cp.exists():
            checkpoint = str(cp)
            break
    else:
        raise RuntimeError("No LTX-2.3 model in /models. Run: modal run chronicles_setup.py::setup")

    upscaler = MODELS_DIR / "ltx-2.3-spatial-upscaler-x2-1.1.safetensors"
    lora = MODELS_DIR / "ltx-2.3-22b-distilled-lora-384-1.1.safetensors"

    for p, label in [(upscaler, "upscaler"), (lora, "LoRA"), (GEMMA_DIR, "Gemma")]:
        if not p.exists():
            raise RuntimeError(f"{label} missing. Run: modal run chronicles_setup.py::setup")

    return TI2VidTwoStagesPipeline(
        checkpoint_path=checkpoint,
        distilled_lora=[LoraPathStrengthAndSDOps(str(lora), 0.6, LTXV_LORA_COMFY_RENAMING_MAP)],
        spatial_upsampler_path=str(upscaler),
        gemma_root=str(GEMMA_DIR),
        loras=[],
        quantization=build_fp8_cast_policy(checkpoint),
    )


def _get_pipeline():
    global _PIPELINE
    if _PIPELINE is None:
        _PIPELINE = _load_pipeline()
    return _PIPELINE


def _build_app():
    web_app = fastapi.FastAPI(title="Chronicles GPU — LTX-2.3")

    @web_app.post("/generate_clip")
    async def generate_clip(request: fastapi.Request):
        import time as _time
        import tempfile
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
        audio_prompt = body.get("audio_prompt", "")
        seed = body.get("seed", 0)
        duration_s = body.get("duration_s", 8)

        if not prompt.strip():
            raise HTTPException(status_code=400, detail="Prompt is required")

        t_load = _time.time()
        try:
            pipeline = _get_pipeline()
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e))
        print(f"[infer] Pipeline loaded in {_time.time() - t_load:.1f}s")

        ref_paths = []
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
                        ref_paths.append({"path": tmp.name, "frame_idx": img.get("frame_idx", 0), "strength": img.get("strength", 1.0)})
                except Exception as e:
                    print(f"  [ref] failed: {e}")

        num_frames = max(9, duration_s * 25 + 1)
        num_frames = ((num_frames - 1) // 8) * 8 + 1
        frame_rate = 25.0
        tiling = TilingConfig.default()

        video_guider = MultiModalGuiderParams(cfg_scale=3.0, stg_scale=1.0, rescale_scale=0.7, modality_scale=3.0, skip_step=0, stg_blocks=[29])
        audio_guider = MultiModalGuiderParams(cfg_scale=7.0, stg_scale=1.0, rescale_scale=0.7, modality_scale=3.0, skip_step=0, stg_blocks=[29])

        images = [ImageConditioningInput(r["path"], r["frame_idx"], r["strength"], 33) for r in ref_paths]

        print(f"[infer] {num_frames}frames/{duration_s}s, {len(images)}refs, seed={seed}")
        t_infer = _time.time()
        combined_prompt = prompt
        if audio_prompt:
            combined_prompt = f"{prompt}\n\n[AUDIO: {audio_prompt}]"
        video, audio = pipeline(
            prompt=combined_prompt, negative_prompt="worst quality, low quality, blurry, distorted, deformed",
            seed=seed, height=512, width=768, num_frames=num_frames, frame_rate=frame_rate,
            num_inference_steps=40, video_guider_params=video_guider, audio_guider_params=audio_guider,
            images=images, tiling_config=tiling,
        )
        print(f"[infer] Denoised in {_time.time() - t_infer:.1f}s")

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            encode_video(video=video, fps=frame_rate, audio=audio, output_path=tmp.name,
                         video_chunks_number=get_video_chunks_number(num_frames, tiling))
            mp4_bytes = Path(tmp.name).read_bytes()
            Path(tmp.name).unlink()

        for r in ref_paths:
            Path(r["path"]).unlink(missing_ok=True)

        elapsed = _time.time() - t0
        print(f"[infer] OK: {len(mp4_bytes)/1e6:.1f}MB in {elapsed:.1f}s")
        return Response(content=mp4_bytes, media_type="video/mp4",
                        headers={"X-Generation-Time-S": f"{elapsed:.1f}", "X-Seed": str(seed),
                                 "X-Frames": str(num_frames), "X-Backend": "ltx-2.3-modal-h200"})

    @web_app.get("/health")
    async def health():
        info = {"status": "ok", "model": "LTX-2.3 22B", "pipeline": "TI2VidTwoStages"}
        if MODELS_DIR.exists():
            info["models_present"] = [f.name for f in MODELS_DIR.iterdir() if f.suffix == ".safetensors" or f.is_dir()]
            expected = MODEL_FILES + ["gemma-3-12b-it-qat-q4_0-unquantized"]
            info["all_models_ready"] = all((MODELS_DIR / e).exists() for e in expected)
        return info

    return web_app


@app.function(gpu="H200", timeout=600, volumes={str(MODELS_DIR): volume}, image=gpu_image)
@modal.asgi_app()
def server():
    import os
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
    return _build_app()
