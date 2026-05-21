#!/bin/bash
# Chronicles GPU Service — IDEMPOTENT SETUP
# Run this ONCE after launching a new instance, or ANY TIME after resume.
# It self-heals: missing packages, stale processes, wrong HF cache paths.
# Usage: bash /home/gpu_service/setup_all.sh

set -e

echo "=== 1/7: Redirect HF cache ==="
export HF_HOME=/home/LTX-Video/hf_cache
grep -q "export HF_HOME=" ~/.bashrc 2>/dev/null || echo "export HF_HOME=/home/LTX-Video/hf_cache" >> ~/.bashrc
rm -rf /home/.cache/huggingface || true
mkdir -p /home/LTX-Video/hf_cache

echo "=== 2/7: Install web server deps ==="
pip install -q fastapi uvicorn httpx pydantic --break-system-packages 2>/dev/null || true

echo "=== 3/7: Clone / update LTX-Video ==="
if [ -d "/home/LTX-Video/.git" ]; then
    cd /home/LTX-Video && git pull -q
else
    cd /home && git clone -q https://github.com/Lightricks/LTX-Video.git
fi

echo "=== 4/7: Install LTX-Video (force reinstall) ==="
cd /home/LTX-Video && pip install -e ".[inference]" --force-reinstall -q --break-system-packages 2>/dev/null || true

echo "=== 5/7: Download model (28.6GB) if missing ==="
if [ ! -f /home/LTX-Video/models/ltxv-13b-0.9.8-distilled.safetensors ]; then
    mkdir -p /home/LTX-Video/models
    HF_HOME=/home/LTX-Video/hf_cache hf download Lightricks/LTX-Video \
        ltxv-13b-0.9.8-distilled.safetensors --local-dir /home/LTX-Video/models/
    # Clean the extra HF cache copy — we already have the file
    rm -rf /home/LTX-Video/hf_cache/hub/models--Lightricks--LTX-Video 2>/dev/null || true
else
    echo "  Model already present — skipping download"
fi

echo "=== 6/7: Kill stale service ==="
pkill -f "python3 app.py" 2>/dev/null || true
sleep 2

echo "=== 7/7: Start GPU service ==="
export HF_HOME=/home/LTX-Video/hf_cache
cd /home/gpu_service && nohup python3 app.py > /tmp/gpu.log 2>&1 &
sleep 8

echo "=== Health check ==="
curl -s http://localhost:6006/health
echo ""
echo "=== DONE ==="
