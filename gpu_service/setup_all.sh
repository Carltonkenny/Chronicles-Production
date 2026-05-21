#!/bin/bash
# Chronicles GPU Service — ONE-SHOT SETUP
# Upload this file to /home/ on the GPU, then: bash setup_all.sh
# Does everything: install deps, clone LTX, download model, start service

set -e

echo "=== 1/5 Installing web server ==="
pip install -q fastapi uvicorn httpx pydantic

echo "=== 2/5 Cloning LTX-Video ==="
cd /home && git clone https://github.com/Lightricks/LTX-Video.git 2>/dev/null || (cd /home/LTX-Video && git pull)

echo "=== 3/5 Installing LTX-Video ==="
cd /home/LTX-Video && pip install -q -e ".[inference]"

echo "=== 4/5 Downloading model (28.6GB, ~60s) ==="
mkdir -p /home/LTX-Video/models
HF_HOME=/home/LTX-Video/hf_cache hf download Lightricks/LTX-Video ltxv-13b-0.9.8-distilled.safetensors --local-dir /home/LTX-Video/models/

echo "=== 5/5 Starting GPU service ==="
cd /home/gpu_service
pkill -f python3 2>/dev/null || true
HF_HOME=/home/LTX-Video/hf_cache nohup python3 app.py > /tmp/gpu.log 2>&1 &
sleep 5
curl -s http://localhost:6006/health
echo ""
echo "=== DONE ==="
