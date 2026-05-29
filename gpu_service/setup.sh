#!/bin/bash
set -euo pipefail

echo "========================================"
echo "Chronicles GPU Service — LTX-2.3 Setup"
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

MODEL_FILE="ltx-2.3-22b-distilled-1.1.safetensors"
GEMMA_DIR="gemma-3-12b-it-qat-q4_0-unquantized"
UPSAMPLER_FILE="ltx-2.3-spatial-upscaler-x2-1.1.safetensors"
LORA_FILE="ltx-2.3-22b-distilled-lora-384-1.1.safetensors"
MODEL_SIZE_GB="42"
echo "  Model: LTX-2.3 22B (distilled 1.1)"

FREE_DISK_GB=$(df -BG /home 2>/dev/null | awk 'NR==2 {gsub(/G/,"",$4); print $4}' || echo "0")
MIN_DISK_GB=$(( $(echo "$MODEL_SIZE_GB" | cut -d. -f1) + 25 ))
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

# ─── 3. Clone LTX-2 ──────────────────────────────────────────────
echo ""
echo "[3/6] LTX-2 repository..."
if [ ! -d "$HOME/LTX-2/.git" ]; then
    echo "  Cloning (first time)..."
    cd "$HOME"
    git clone https://github.com/Lightricks/LTX-2.git
else
    echo "  Already cloned, updating..."
    cd "$HOME/LTX-2"
    git pull -q
fi

echo "  Installing LTX-2 packages..."
cd "$HOME/LTX-2"
pip install -e packages/ltx-core -q 2>&1 | tail -1 || pip install -e packages/ltx-core -q --break-system-packages 2>&1 | tail -1
pip install -e packages/ltx-pipelines -q 2>&1 | tail -1 || pip install -e packages/ltx-pipelines -q --break-system-packages 2>&1 | tail -1
echo "  LTX-2 OK"

# ─── 4. Download models ─────────────────────────────────────────
echo ""
echo "[4/6] Model weights (~${MODEL_SIZE_GB}GB)..."
MODELS_DIR="$HOME/LTX-2/models"
mkdir -p "$MODELS_DIR"

MODEL_PATH="$MODELS_DIR/$MODEL_FILE"
UPSAMPLER_PATH="$MODELS_DIR/$UPSAMPLER_FILE"
LORA_PATH="$MODELS_DIR/$LORA_FILE"
GEMMA_PATH="$MODELS_DIR/$GEMMA_DIR"

check_hf_auth() {
    if ! huggingface-cli whoami &>/dev/null; then
        echo ""
        echo "  ============================================="
        echo "  HuggingFace login REQUIRED"
        echo "  ============================================="
        echo "  1. Go to https://huggingface.co/settings/tokens"
        echo "  2. Create a token (or copy an existing one)"
        echo "  3. Paste it below"
        echo "  ============================================="
        echo ""
        huggingface-cli login
    fi
}

if [ -f "$MODEL_PATH" ]; then
    echo "  LTX-2.3 model: already downloaded, skipping"
else
    check_hf_auth
    echo "  Downloading LTX-2.3 22B distilled 1.1 (42GB, may take 10-15 min)..."
    huggingface-cli download Lightricks/LTX-2.3 \
        "$MODEL_FILE" \
        --local-dir "$MODELS_DIR/"
fi

if [ -f "$UPSAMPLER_PATH" ]; then
    echo "  Upscaler: already downloaded, skipping"
else
    check_hf_auth
    echo "  Downloading spatial upscaler..."
    huggingface-cli download Lightricks/LTX-2.3 \
        "$UPSAMPLER_FILE" \
        --local-dir "$MODELS_DIR/"
fi

if [ -f "$LORA_PATH" ]; then
    echo "  Distilled LoRA: already downloaded, skipping"
else
    check_hf_auth
    echo "  Downloading distilled LoRA..."
    huggingface-cli download Lightricks/LTX-2.3 \
        "$LORA_FILE" \
        --local-dir "$MODELS_DIR/"
fi

if [ -d "$GEMMA_PATH" ]; then
    echo "  Gemma text encoder: already downloaded, skipping"
else
    check_hf_auth
    echo "  Downloading Gemma 3 text encoder..."
    huggingface-cli download google/gemma-3-12b-it-qat-q4_0-unquantized \
        --local-dir "$GEMMA_PATH/"
fi
echo "  Downloads complete"

# ─── 5. Generate .env for the service ────────────────────────────
echo ""
echo "[5/6] Creating .env configuration..."
cat > "$SCRIPT_DIR/.env" << ENVEOF
GPU_API_KEY=chronicles-gpu-key-2026
LTX_2_DIR=$HOME/LTX-2
MODEL_WEIGHTS_PATH=$MODEL_PATH
GEMMA_ROOT=$GEMMA_PATH
SPATIAL_UPSAMPLER_PATH=$UPSAMPLER_PATH
DISTILLED_LORA_PATH=$LORA_PATH
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

if [ -d "$GEMMA_PATH" ]; then
    echo "  Gemma encoder: $GEMMA_PATH OK"
else
    echo "  WARNING: Gemma not found — text-to-video may fail"
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
