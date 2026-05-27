#!/bin/bash
set -euo pipefail

echo "========================================"
echo "Chronicles GPU Service — Resume Start"
echo "========================================"

# Kill any existing instance on port 6006
echo "[1/4] Cleaning up old processes..."
pkill -f "uvicorn app:app" 2>/dev/null || true
sleep 2

# Reinstall pip packages that get wiped on pause/resume
echo "[2/4] Restoring pip packages..."
pip install -q fastapi uvicorn httpx pydantic tiktoken protobuf sentencepiece 2>/dev/null || \
    pip install -q fastapi uvicorn httpx pydantic tiktoken protobuf sentencepiece --break-system-packages 2>/dev/null || true

# Check CUDA
echo "[3/4] Validating GPU..."
python3 -c "
import torch
if not torch.cuda.is_available():
    print('FATAL: CUDA not available')
    exit(1)
print(f'GPU: {torch.cuda.get_device_name(0)}')
print(f'VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB')
" || echo "  WARNING: GPU check failed"

# Start the service
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "[4/4] Starting GPU service on port 6006..."
cd "$SCRIPT_DIR" && nohup python3 app.py > /tmp/gpu.log 2>&1 &
sleep 8

echo ""
echo "=== Health check ==="
curl -s http://localhost:6006/health | python3 -m json.tool 2>/dev/null || echo "  Health check failed — check /tmp/gpu.log"
echo ""
echo "=== Last 10 lines of log ==="
tail -10 /tmp/gpu.log 2>/dev/null || true
echo ""
echo "=== Ready ==="
