#!/bin/bash
set -euo pipefail

echo "========================================"
echo "Chronicles GPU Service — Idempotent Setup"
echo "========================================"

# ─── 0. Validate environment ──────────────────────────────────────
echo ""
echo "[0/6] Validating environment..."

if ! command -v nvidia-smi &>/dev/null; then
    echo "FATAL: nvidia-smi not found. This script MUST run on a GPU instance."
    echo "  Launch PyTorch 2.5+ template on JarvisLabs, then re-run."
    exit 1
fi

GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)
GPU_MEM_MB=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
echo "  GPU: $GPU_NAME ($GPU_MEM_MB MB VRAM)"

if [ "$GPU_MEM_MB" -ge 48000 ]; then
    MODEL_FILE="ltxv-13b-0.9.8-distilled.safetensors"
    MODEL_CONFIG="configs/ltxv-13b-0.9.8-distilled.yaml"
    MODEL_SIZE_GB="28.6"
    echo "  VRAM >= 48GB → using BF16 model (best quality)"
else
    MODEL_FILE="ltxv-13b-0.9.8-distilled-fp8.safetensors"
    MODEL_CONFIG="configs/ltxv-13b-0.9.8-distilled-fp8.yaml"
    MODEL_SIZE_GB="13"
    echo "  VRAM < 48GB → using FP8 model (compact)"
fi

FREE_DISK_GB=$(df -BG /home 2>/dev/null | awk 'NR==2 {gsub(/G/,"",$4); print $4}' || echo "0")
MIN_DISK_GB=$(( $(echo "$MODEL_SIZE_GB" | cut -d. -f1) + 15 ))
if [ "$FREE_DISK_GB" -lt "$MIN_DISK_GB" ]; then
    echo "FATAL: Only ${FREE_DISK_GB}GB free on /home, need ${MIN_DISK_GB}GB+"
    echo "  Re-launch instance with larger disk (100GB+ recommended)"
    exit 1
fi
echo "  Disk: ${FREE_DISK_GB}GB free (need ${MIN_DISK_GB}GB) OK"

# ─── 1. System packages ──────────────────────────────────────────
echo ""
echo "[1/6] System packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq ffmpeg git-lfs 2>/dev/null || echo "  (non-critical packages skipped)"

# ─── 2. Python dependencies ──────────────────────────────────────
echo ""
echo "[2/6] Python dependencies..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
pip install -q -r "$SCRIPT_DIR/requirements.txt" 2>&1 | tail -1 || {
    echo "  Trying without --break-system-packages..."
    pip install -q -r "$SCRIPT_DIR/requirements.txt" --break-system-packages 2>&1 | tail -1 || {
        echo "FATAL: pip install failed"
        exit 1
    }
}

# ─── 3. Clone LTX-Video ──────────────────────────────────────────
echo ""
echo "[3/6] LTX-Video repository..."
if [ ! -d "$HOME/LTX-Video/.git" ]; then
    echo "  Cloning (first time)..."
    cd "$HOME"
    git clone https://github.com/Lightricks/LTX-Video.git
else
    echo "  Already cloned, updating..."
    cd "$HOME/LTX-Video"
    git pull -q
fi

echo "  Installing LTX-Video inference package..."
cd "$HOME/LTX-Video"
pip install -e ".[inference]" -q 2>&1 | tail -1 || pip install -e ".[inference]" -q --break-system-packages 2>&1 | tail -1
echo "  LTX-Video OK"

# ─── 4. Download model weights ───────────────────────────────────
echo ""
echo "[4/6] Model weights (${MODEL_SIZE_GB}GB)..."
MODEL_PATH="$HOME/LTX-Video/models/$MODEL_FILE"
mkdir -p "$HOME/LTX-Video/models"

if [ -f "$MODEL_PATH" ]; then
    echo "  Already downloaded, skipping"
else
    echo "  Checking HuggingFace auth..."
    if ! huggingface-cli whoami &>/dev/null; then
        echo ""
        echo "  ============================================="
        echo "  HuggingFace login REQUIRED"
        echo "  ============================================="
        echo "  LTX-Video is a gated model — you must:"
        echo "    1. Go to https://huggingface.co/settings/tokens"
        echo "    2. Create a token (or copy an existing one)"
        echo "    3. Paste it below"
        echo "  ============================================="
        echo ""
        huggingface-cli login
    fi

    echo "  Accept model terms at: https://huggingface.co/Lightricks/LTX-Video"
    echo "  (Do this once, before downloading)"
    echo "  Downloading (may take 5-10 min)..."
    huggingface-cli download Lightricks/LTX-Video \
        "$MODEL_FILE" \
        --local-dir "$HOME/LTX-Video/models/"
    echo "  Download complete"
fi

# ─── 5. Generate .env for the service ────────────────────────────
echo ""
echo "[5/6] Creating .env configuration..."
cat > "$SCRIPT_DIR/.env" << ENVEOF
GPU_API_KEY=chronicles-gpu-key-2026
LTX_VIDEO_DIR=$HOME/LTX-Video
MODEL_WEIGHTS_PATH=$MODEL_PATH
PIPELINE_CONFIG=$MODEL_CONFIG
PORT=6006
ENVEOF
echo "  Created $SCRIPT_DIR/.env"

# ─── 6. Validation ───────────────────────────────────────────────
echo ""
echo "[6/6] Validation..."
python3 -c "
import torch, sys
print(f'  PyTorch: {torch.__version__}')
print(f'  CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'  GPU: {torch.cuda.get_device_name(0)}')
    print(f'  VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB')
    sys.exit(0)
else:
    print('  FATAL: CUDA not available. Check GPU driver.')
    sys.exit(1)
"

if [ -f "$MODEL_PATH" ]; then
    MODEL_BYTES=$(stat -c%s "$MODEL_PATH" 2>/dev/null || echo "0")
    echo "  Model file: $MODEL_PATH ($(( MODEL_BYTES / 1073741824 ))GB) OK"
else
    echo "  FATAL: Model file not found at $MODEL_PATH"
    exit 1
fi

if [ -f "$HOME/LTX-Video/$MODEL_CONFIG" ]; then
    echo "  Config file: $HOME/LTX-Video/$MODEL_CONFIG OK"
else
    echo "  WARNING: Config not found — inference may fail"
fi

echo ""
echo "========================================"
echo "SETUP COMPLETE — NO ERRORS"
echo "========================================"
echo ""
echo "Start the service:"
echo ""
echo "  cd $SCRIPT_DIR && uvicorn app:app --host 0.0.0.0 --port 6006"
echo ""
echo "Or with auth:"
echo ""
echo "  GPU_API_KEY=chronicles-gpu-key-2026 uvicorn app:app --host 0.0.0.0 --port 6006"
echo ""
echo "Test it:"
echo ""
echo "  curl http://localhost:6006/health"
echo "  curl -X POST http://localhost:6006/generate_clip -H 'Content-Type: application/json' -d '{\"prompt\":\"A cinematic shot of a viking forge\",\"duration_s\":5,\"seed\":42}' --output test.mp4"
echo ""
