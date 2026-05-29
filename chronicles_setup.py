"""
Chronicles GPU Setup — Downloads LTX-2.3 models to Modal Volume.
========================================================================
Run once before deployment. CPU-only, free.

Usage: modal run chronicles_setup.py::setup
"""
import time as _time
from pathlib import Path

import modal

MODELS_DIR = Path("/models")
HUGGINGFACE_REPO = "Lightricks/LTX-2.3"

MODEL_FILES = [
    "ltx-2.3-22b-distilled-1.1.safetensors",
    "ltx-2.3-spatial-upscaler-x2-1.1.safetensors",
    "ltx-2.3-22b-distilled-lora-384-1.1.safetensors",
]

GEMMA_REPO = "google/gemma-3-12b-it-qat-q4_0-unquantized"
GEMMA_DIR = MODELS_DIR / "gemma-3-12b-it-qat-q4_0-unquantized"

app = modal.App("chronicles-gpu")
volume = modal.Volume.from_name("ltx2-models", create_if_missing=True)

setup_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("huggingface_hub[hf_transfer]>=0.28")
)


@app.function(
    cpu=4.0,
    memory=8192,
    timeout=3600,
    volumes={str(MODELS_DIR): volume},
    image=setup_image,
    secrets=[modal.Secret.from_name("hf-secret")],
)
def setup():
    """Download all LTX-2.3 model weights + tokenizer to Modal Volume."""
    from huggingface_hub import hf_hub_download, snapshot_download

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    t_start = _time.time()

    for idx, filename in enumerate(MODEL_FILES, 1):
        dest = MODELS_DIR / filename
        if dest.exists():
            size_gb = dest.stat().st_size / 1e9
            print(f"[{idx}/4] SKIP {filename} ({size_gb:.1f} GB, already exists)")
            continue
        print(f"[{idx}/4] DOWNLOAD {filename}...")
        _t = _time.time()
        hf_hub_download(HUGGINGFACE_REPO, filename, local_dir=str(MODELS_DIR), local_dir_use_symlinks=False)
        size_gb = Path(hf_hub_download.__wrapped__ if hasattr(hf_hub_download, '__wrapped__') else "").stat().st_size / 1e9 if False else MODELS_DIR / filename
        print(f"  OK: {(MODELS_DIR / filename).stat().st_size / 1e9:.1f} GB in {_time.time() - _t:.0f}s")

    if GEMMA_DIR.exists() and any(GEMMA_DIR.iterdir()):
        print("[4/4] SKIP Gemma text encoder (already downloaded)")
    else:
        print("[4/4] DOWNLOAD Gemma text encoder (may take 10-15 min)...")
        _t = _time.time()
        snapshot_download(GEMMA_REPO, local_dir=str(GEMMA_DIR), local_dir_use_symlinks=False)
        n = sum(1 for _ in GEMMA_DIR.rglob("*") if _.is_file())
        print(f"  OK: {n} files in {_time.time() - _t:.0f}s")

    tokenizer_file = GEMMA_DIR / "tokenizer.model"
    if not tokenizer_file.exists():
        print("  Downloading Gemma tokenizer + config files (separate repo)...")
        _t = _time.time()
        import os as _os
        snapshot_download("google/gemma-3-12b-it", local_dir=str(GEMMA_DIR),
            allow_patterns=["tokenizer.model", "*.json"],
            token=_os.environ.get("HF_TOKEN"))
        file_count = sum(1 for _ in GEMMA_DIR.rglob("*") if _.is_file())
        print(f"  OK: {file_count} files in {_time.time() - _t:.0f}s")

    elapsed = _time.time() - t_start
    print(f"\n=== SETUP COMPLETE in {elapsed:.0f}s ({elapsed/60:.0f} min) ===")
    print("\nVerification:")
    all_ok = True
    for f in MODEL_FILES:
        ok = (MODELS_DIR / f).exists()
        print(f"  {'OK' if ok else 'MISSING'}: {f}")
        if not ok: all_ok = False
    ok = GEMMA_DIR.exists()
    print(f"  {'OK' if ok else 'MISSING'}: {GEMMA_DIR.name}")
    if not ok: all_ok = False
    ok = tokenizer_file.exists()
    print(f"  {'OK' if ok else 'MISSING'}: tokenizer.model")
    if not ok: all_ok = False

    if all_ok:
        print("\nALL MODELS READY. Deploy now: modal deploy chronicles_modal.py")
    else:
        print("\nSOME MODELS MISSING. Re-run: modal run chronicles_setup.py::setup")
        raise SystemExit(1)
