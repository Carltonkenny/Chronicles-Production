# Chronicles GPU Video Service

FastAPI server that runs **LTX-Video 13B** inference on a JarvisLabs GPU instance.
Chronicles backend sends prompts → this service generates MP4 clips → returns them.

**Supported GPUs:** L4 24GB (FP8), A100 40/80GB (BF16), H100 (BF16)

---

## Pre-Launch Checklist

Before you start a paid instance, have these ready:

- [ ] **JarvisLabs account** with ₹500+ credit
- [ ] **HuggingFace token** — create at https://huggingface.co/settings/tokens
- [ ] **Accept LTX-Video terms** — visit https://huggingface.co/Lightricks/LTX-Video and click "Agree and access repository"

---

## Launch the Instance

1. Dashboard → **Launch** → Search for **A100-80GB** or **L4**
2. Template: **PyTorch 2.5** (CUDA + torch pre-installed)
3. Pricing: **Spot** (40-56% cheaper than on-demand)
4. Disk: **100GB minimum** (model is 13-28GB + repo + deps)
5. **HTTP ports:** Make sure **6006** is in the reserved list (it shows as reserved by default)
6. Name: `chronicles-gpu`

---

## One-Time Setup (20 min total)

### Step 1: Connect & Copy Files

Get the SSH command from your JarvisLabs dashboard:

```bash
# On your local machine:
scp -P <port> -r gpu_service/ user@<ip>:~/
```

### Step 2: Run Setup

```bash
# On the GPU instance:
cd ~/gpu_service
bash setup.sh
```

The script will:
1. Validate GPU, disk space, Python version
2. Install system packages (ffmpeg, git-lfs)
3. Install Python dependencies (FastAPI, PyTorch, diffusers, etc.)
4. Clone LTX-Video repo and install inference package
5. Auto-detect GPU VRAM and download the right model:
   - **≥40GB VRAM** → BF16 model (28.6GB, best quality) — A100/H100
   - **<40GB VRAM** → FP8 model (13GB, compact) — L4
6. Run validation (CUDA check, model file check)

If prompted, paste your HuggingFace token when asked.

### Step 3: Verify Setup

```bash
# Check the health endpoint (before starting full service):
python3 -c "
import torch
print(f'CUDA: {torch.cuda.is_available()}')
print(f'GPU: {torch.cuda.get_device_name(0)}')
print(f'VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB')
"

# Check model file
ls -la ~/LTX-Video/models/
```

### Step 4: Start the Service

```bash
cd ~/gpu_service
GPU_API_KEY="chronicles-gpu-key-2026" uvicorn app:app --host 0.0.0.0 --port 6006
```

Expected output:
```
============================================================
 Chronicles GPU Video Service
============================================================
 Model:   LTX-Video 13B distilled BF16
 Repo:    /home/LTX-Video
 Weights: /home/LTX-Video/models/ltxv-13b-0.9.8-distilled.safetensors
 Auth:    ENABLED
 Port:    6006
```

Keep this terminal open.

### Step 5: Test It

In a second terminal (SSH into the GPU instance again):

```bash
# Health check
curl http://localhost:6006/health

# Generate a 5-second test clip
curl -X POST http://localhost:6006/generate_clip \
  -H "Content-Type: application/json" \
  -H "X-API-Key: chronicles-gpu-key-2026" \
  -d '{"prompt":"A cinematic shot of a viking blacksmith striking an anvil, sparks flying, warm forge lighting","duration_s":5,"seed":42}' \
  --output test.mp4 && ls -lah test.mp4
```

First clip takes ~55s (model loads into VRAM once). Subsequent clips skip model loading and take ~30-50s each.

---

## Wire Into Chronicles Backend

Get the instance IP from your JarvisLabs dashboard → `chronicles-gpu` → **API Endpoint** (looks like `https://xxx.jarvislabs.ai`).

On your local Chronicles backend, create/update `.env`:

```env
VIDEO_PROVIDER=cloud_gpu
CLOUD_GPU_ENDPOINT=https://xxx.jarvislabs.ai
CLOUD_GPU_API_KEY=chronicles-gpu-key-2026
```

Restart Chronicles backend. Now film generation sends video work to the GPU.

---

## Daily Use: Stop/Start

| Action | What happens | Cost |
|--------|-------------|------|
| **START** (JarvisLabs dashboard) | Instance boots (~90s) | ₹74.52/hr (A100 40GB spot) |
| **Generate clips** | ~40-60s per clip on A100 | ~₹7.45/film (6 clips) |
| **STOP** (dashboard) | GPU released, disk preserved | ₹0/hr (disk: ~₹10/month) |

**Your workflow after STOP:**
1. Click **START** in JarvisLabs dashboard
2. Wait ~90s for boot
3. SSH in and run: `cd ~/gpu_service && bash start.sh`
4. Generate films from Chronicles
5. Click **STOP** when done

---

## Cost per Film

| GPU | Spot/hr | Per clip | 6 clips | Per film | ₹500 covers |
|-----|---------|----------|---------|----------|-------------|
| **L4 24GB** | ₹41 | ~90s | 9 min | **₹6.15** | 81 films |
| **A100 40GB** | ₹74.52 | ~40-60s | 4-6 min | **₹7.45** | 34 films |
| **A100 80GB** | ₹140.94 | ~30-50s | 3-5 min | **₹11.75** | 22 films |
| **H100** | ₹283.50 | ~10s | 60s | **₹4.73** | 53 films |

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `huggingface-cli: command not found` | HF CLI not installed | `pip install huggingface-hub` |
| Model download fails with 401 | Not logged into HuggingFace | `huggingface-cli login` |
| Health says `model_ready: false` | Model or repo not found | Re-run: `bash setup.sh` |
| Health says CUDA not available | Wrong template (no GPU drivers) | Re-launch with PyTorch 2.5 template |
| Connection refused on port 6006 | Service not running or wrong port | Check `ps aux \| grep uvicorn` |
| Inference returns empty MP4 | Model/config mismatch | Check stderr in service logs |
| `ModuleNotFoundError: ltx_video` | LTX-Video not installed | `cd ~/LTX-Video && pip install -e ".[inference]"` |

---

## Files in this Folder

| File | Purpose |
|------|---------|
| `app.py` | FastAPI server — POST /generate_clip + GET /health |
| `setup.sh` | **Use this.** One-time idempotent setup (auto-detect GPU, download model, validate) |
| `start.sh` | Quick start after JarvisLabs resume (reinstalls lost pip packages) |
| `requirements.txt` | Python dependencies |
| `.env.example` | Configuration template |
| `Dockerfile` | Container image (alternative to manual setup) |
| `deploy.sh` | Auto-deploy from local machine to JarvisLabs (Linux/macOS only) |
| `README.md` | This file |

---

## Architecture

```
Chronicles Backend          GPU Instance (JarvisLabs)
  ┌──────────────┐          ┌───────────────────────┐
  │ VideoLead    │  HTTP    │ FastAPI on :6006       │
  │ CloudGPU     │─────────▶│ LTX-Video 13B inference│
  │ Provider     │  MP4     │ Model in VRAM          │
  └──────────────┘◀─────────└───────────────────────┘
```
