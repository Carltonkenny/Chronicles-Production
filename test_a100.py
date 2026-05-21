import httpx, json, time

url = "https://dda1414139441.notebooksn.jarvislabs.net"

r = httpx.get(url + "/health", timeout=10)
d = r.json()
print("=== A100-80GB is LIVE ===")
print("Status:", d["status"])
print("GPU:", d["gpu"]["name"])
print("VRAM free:", d["gpu"]["vram_free_gb"], "GB")
print("Ready:", d["model_ready"])
print("Weights:", d["weights_found"])

if d["model_ready"] and d["weights_found"]:
    print()
    print("Generating 5s cinematic clip...")
    t0 = time.time()
    r2 = httpx.post(
        url + "/generate_clip",
        json={
            "prompt": "A cinematic shot of a blacksmith striking an anvil at dawn, sparks flying, warm forge fire, photorealistic, 35mm wide shot",
            "duration_s": 5,
            "seed": 42,
        },
        timeout=600,
    )
    dt = time.time() - t0
    if r2.status_code == 200:
        print(f"SUCCESS! {len(r2.content)//1024} KB in {int(dt)}s!")
        with open(
            "C:/Users/user/OneDrive/Desktop/Chronicles-Production/backend/generated/a100_first_clip.mp4",
            "wb",
        ) as f:
            f.write(r2.content)
        print("Saved to generated/a100_first_clip.mp4")
    else:
        print(f"FAILED: {r2.status_code}")
        print(r2.text[:300])
else:
    print("Service not ready yet — run start.sh first")
