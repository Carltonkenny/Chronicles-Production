#!/bin/bash
# ─── Chronicles GPU Service — One-Time Setup ───────────────────────
# Run this on the JarvisLabs L4 instance after launching it.
# This clones LTX-Video, downloads model weights, installs deps.
#
# Usage: bash setup.sh
#
# Requires: PyTorch 2.5+ CUDA template (JarvisLabs default)
# ──────────────────────────────────────────────────────────────────

set -e

echo "========================================"
echo "Chronicles GPU Service — Setup"
echo "========================================"

# ─── 1. Install system deps ───────────────────────────────────────
echo ""
echo "[1/4] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq ffmpeg git-lfs 2>/dev/null || true

# ─── 2. Clone LTX-Video repo ──────────────────────────────────────
echo ""
echo "[2/4] Cloning LTX-Video..."
if [ ! -d "$HOME/LTX-Video" ]; then
    git clone https://github.com/Lightricks/LTX-Video.git "$HOME/LTX-Video"
    cd "$HOME/LTX-Video"
    pip install -e ".[inference]" -q
else
    echo "LTX-Video already cloned, updating..."
    cd "$HOME/LTX-Video"
    git pull
    pip install -e ".[inference]" -q
fi

# ─── 3. Create models dir ─────────────────────────────────────────
echo ""
echo "[3/4] Setting up model weights directory..."
mkdir -p "$HOME/LTX-Video/models"

# ─── 4. Install our service dependencies ──────────────────────────
echo ""
echo "[4/4] Installing GPU service dependencies..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
pip install -r requirements.txt -q

# ─── 5. Instructions for weights ──────────────────────────────────
echo ""
echo "========================================"
echo "SETUP COMPLETE"
echo "========================================"
echo ""
echo "NEXT: Download model weights (~13GB, ~5 min):"
echo ""
echo "  cd ~/LTX-Video"
echo "  huggingface-cli download Lightricks/LTX-Video \\"
echo "    ltxv-13b-0.9.8-distilled-fp8.safetensors \\"
echo "    --local-dir models/"
echo ""
echo "Then start the service:"
echo ""
echo "  cd $SCRIPT_DIR"
echo "  GPU_API_KEY=\"your-secret-key\" uvicorn app:app --host 0.0.0.0 --port 8080"
echo ""
echo "Test it:"
echo ""
echo "  curl http://localhost:8080/health"
echo "  curl -X POST http://localhost:8080/generate_clip \\"
echo '    -H "Content-Type: application/json" \'
echo '    -d "{\"prompt\":\"A cinematic shot of a viking forge\",\"duration_s\":5,\"seed\":42}" \'
echo "    --output test.mp4"
echo ""
