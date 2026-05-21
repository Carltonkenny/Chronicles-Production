#!/bin/bash
# Chronicles GPU Service — Start after resume
# This re-installs ephemeral pip packages that get wiped on pause/resume.
# Usage: bash /home/gpu_service/start.sh

set -e
echo "=== Restoring pip packages ==="
pip install -q fastapi uvicorn httpx pydantic

echo "=== Starting GPU service ==="
cd /home/gpu_service && nohup python3 app.py > /tmp/gpu.log 2>&1 &
sleep 5
echo "=== Health check ==="
curl -s http://localhost:6006/health
echo ""
echo "=== Ready ==="
