#!/bin/bash
# ─── Chronicles GPU Service — Auto Deploy ─────────────────────────
# One command deploys everything to a running JarvisLabs instance.
# Usage: bash deploy.sh <jl-instance-name>
# Example: bash deploy.sh chronicles-gpu
#
# What it does:
#   1. Copies gpu_service files to the GPU instance
#   2. Runs setup (clones LTX-Video, installs deps)
#   3. Downloads model weights (~13GB, 5 min)
#   4. Optionally starts the service
# ──────────────────────────────────────────────────────────────────

set -e
INSTANCE="${1:-chronicles-gpu}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "========================================"
echo "Chronicles GPU Service — Deploy"
echo "========================================"
echo "Target: $INSTANCE"
echo ""

# Step 1: Copy files
echo "[1/4] Copying gpu_service files to $INSTANCE..."
echo "  Files: app.py, requirements.txt, setup.sh"
scp -q "$SCRIPT_DIR/app.py" "$SCRIPT_DIR/requirements.txt" \
    "$SCRIPT_DIR/setup.sh" \
    "jarvislabs:${INSTANCE}:~/gpu_service/" 2>/dev/null || {
    # Fallback: use jl ssh to get connection
    echo "  Getting SSH details..."
    SSH_CMD=$(jl ssh --name "$INSTANCE" --get-command 2>/dev/null)
    if [ -z "$SSH_CMD" ]; then
        echo "  ERROR: Could not get SSH command. Is the instance running?"
        echo "  Check: jl list"
        exit 1
    fi
    HOST=$(echo "$SSH_CMD" | grep -oP '(?<=@)[^ ]+' | head -1 || echo "")
    PORT=$(echo "$SSH_CMD" | grep -oP '(?<=-p )\d+' | head -1 || echo "22")
    if [ -n "$HOST" ]; then
        scp -P "$PORT" -q "$SCRIPT_DIR/app.py" "$SCRIPT_DIR/requirements.txt" \
            "$SCRIPT_DIR/setup.sh" "user@${HOST}:~/gpu_service/"
    fi
}
echo "  Done."

# Step 2: Run setup
echo ""
echo "[2/4] Running setup.sh on $INSTANCE..."
SSH_CMD=$(jl ssh --name "$INSTANCE" --get-command 2>/dev/null)
if [ -z "$SSH_CMD" ]; then
    echo "  ERROR: Cannot get SSH connection"
    exit 1
fi
$SSH_CMD "cd ~/gpu_service && bash setup.sh"
echo "  Setup complete."

# Step 3: Download model weights
echo ""
echo "[3/4] Downloading LTX-Video model weights (13GB, ~5 min)..."
$SSH_CMD "
    cd ~/LTX-Video
    mkdir -p models
    if [ -f models/ltxv-13b-0.9.8-distilled-fp8.safetensors ]; then
        echo '  Weights already downloaded (skipping).'
    else
        huggingface-cli download Lightricks/LTX-Video \
            ltxv-13b-0.9.8-distilled-fp8.safetensors \
            --local-dir models/
        echo '  Download complete.'
    fi
"
echo "  Weights ready."

# Step 4: Instructions
echo ""
echo "========================================"
echo "DEPLOY COMPLETE"
echo "========================================"
echo ""
echo "Start the service:"
echo ""
echo "  jl ssh --name $INSTANCE"
echo "  cd ~/gpu_service"
echo "  GPU_API_KEY=chronicles-gpu-key-2026 uvicorn app:app --host 0.0.0.0 --port 6006"
echo ""
echo "Or run it in background:"
echo ""
echo "  SSH_CMD=\$(jl ssh --name $INSTANCE --get-command)"
echo "  \$SSH_CMD 'cd ~/gpu_service && nohup uvicorn app:app --host 0.0.0.0 --port 6006 > /tmp/chronicles-gpu.log 2>&1 &'"
echo ""
echo "Get API endpoint URL from: JarvisLabs dashboard → $INSTANCE → API Endpoint"
echo "Then set in Chronicles .env:"
echo "  CLOUD_GPU_ENDPOINT=https://xxx.jarvislabs.ai"
echo "  CLOUD_GPU_API_KEY=chronicles-gpu-key-2026"
echo ""
