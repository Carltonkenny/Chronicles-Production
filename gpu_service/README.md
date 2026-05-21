# Chronicles GPU Video Service

The GPU-side service that generates video clips. Runs on JarvisLabs L4 24GB.
Chronicles backend sends prompts → this service runs LTX-Video → returns MP4.

---

## Setup Instructions (20 minutes total)

### Step 1: Create JarvisLabs account

1. Go to https://jarvislabs.ai → Sign Up → Verify email
2. Go to **Billing** → **Add Credit** → Deposit **₹500** via UPI/card
   - ₹500 covers ~138 films (₹3.60/film)

### Step 2: Launch L4 spot instance

1. Dashboard → **Launch** → Search for **L4 24GB**
2. Template: **PyTorch 2.5** (has CUDA, torch pre-installed)
3. Check **"Spot pricing"** (56% cheaper: ₹18/hr instead of ₹41)
4. Disk: **50GB** minimum
5. Boot time: ~90 seconds

### Step 3: Connect to the instance

Once the instance shows "Running" in the dashboard:

```bash
# Copy the SSH command from JarvisLabs dashboard (looks like:)
ssh -p 12345 user@123.456.789.0
```

When prompted, use the password shown in JarvisLabs dashboard.

### Step 4: Copy the GPU service files to the instance

On your local machine (where Chronicles is):

```bash
# From the Chronicles-Production folder:
scp -P 12345 -r gpu_service/ user@123.456.789.0:~/gpu_service/
```

### Step 5: Run the one-time setup

On the L4 instance (after SSH):

```bash
cd ~/gpu_service
bash setup.sh
```

This takes ~5 minutes. It installs:
- LTX-Video inference code
- PyTorch, diffusers, FastAPI
- FFmpeg for video processing

### Step 6: Download the model weights

Still on the L4 instance:

```bash
cd ~/LTX-Video
huggingface-cli download Lightricks/LTX-Video \
  ltxv-13b-0.9.8-distilled-fp8.safetensors \
  --local-dir models/
```

This downloads ~13GB and takes ~5 minutes. Only needed once.

### Step 7: Start the video service

```bash
cd ~/gpu_service
GPU_API_KEY="my-secret-key-change-me" uvicorn app:app --host 0.0.0.0 --port 8080
```

You should see:
```
Chronicles GPU Video Service
 Model:   LTX-Video 13B distilled FP8
 GPU:     NVIDIA L4 (23.5 GB VRAM)
 Service ready
```

Keep this terminal open. The service is now running.

### Step 8: Test it

Open a second terminal, SSH into the L4 again, and test:

```bash
# Health check
curl http://localhost:8080/health

# Generate a 5-second test clip
curl -X POST http://localhost:8080/generate_clip \
  -H "Content-Type: application/json" \
  -H "X-API-Key: my-secret-key-change-me" \
  -d '{"prompt":"A cinematic shot of a viking blacksmith striking an anvil, sparks flying, warm forge lighting","duration_s":5,"seed":42}' \
  --output test.mp4
```

This takes ~60-90s for the first clip (model loads from disk).
Subsequent clips are faster (~60s each).

### Step 9: Wire into Chronicles backend

Get the L4 instance IP from JarvisLabs dashboard (the same one you SSH'd to).
On your local Chronicles backend, edit `.env`:

```env
VIDEO_PROVIDER=cloud_gpu
CLOUD_GPU_ENDPOINT=http://123.456.789.0:8080
CLOUD_GPU_API_KEY=my-secret-key-change-me
```

Restart Chronicles. Now when you generate a film, it sends video work to the L4.

---

## Daily Usage: Stop/Start the GPU

To avoid paying when not in use:

```
Generate films → DONE → STOP instance → IDLE → START → Generate more
```

| Action | What happens | Cost |
|--------|-------------|------|
| **START** (JarvisLabs dashboard) | Instance boots (~90s), model loads (~30s) | ₹18/hr |
| **Generate films** | Service runs, ~12 min per film | ₹3.60/film |
| **STOP** (JarvisLabs dashboard) | GPU released, disk preserved | ₹0/hr (disk: ~₹5/month) |
| **START again** | Model loads from disk (~30s), no re-download | ₹18/hr |

**Your workflow:**
1. Open JarvisLabs dashboard
2. Click **START** on your L4 instance
3. Wait ~90s for boot
4. SSH in and run: `cd ~/gpu_service && uvicorn app:app --host 0.0.0.0 --port 8080`
5. Generate films from Chronicles
6. When done: Ctrl+C to stop the service
7. Click **STOP** on the dashboard
8. Total cost per session: ~₹4-5

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: ltx_video` | Run `cd ~/LTX-Video && pip install -e ".[inference]"` |
| CUDA out of memory | Reduce `duration_s` in the request (max 15s on L4) |
| Connection refused on port 8080 | Make sure uvicorn is running (`ps aux | grep uvicorn`) |
| Model weights not found | Check `ls -la ~/LTX-Video/models/` — re-download if empty |
| Inference returns empty MP4 | Check `stderr` in the service logs for model errors |

---

## Files in this folder

| File | Purpose |
|------|---------|
| `app.py` | FastAPI server — the main service (80 lines) |
| `requirements.txt` | Python dependencies |
| `setup.sh` | One-time setup script (clones LTX, installs deps) |
| `Dockerfile` | Container image (alternative to manual setup) |
| `README.md` | This file |

## Architecture

```
Chronicles Backend          L4 GPU (JarvisLabs)
  ┌──────────────┐          ┌────────────────────┐
  │ VideoLead    │  HTTP    │ FastAPI on :8080   │
  │ CloudGPU     │─────────▶│ LTX-Video 13B FP8  │
  │ Provider     │  MP4     │ inference.py       │
  └──────────────┘◀─────────└────────────────────┘
```
