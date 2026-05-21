"""Direct L4 video generation — no LLM needed. Uses Film 1 saved data."""
import sys, asyncio, json, time, logging, httpx
from pathlib import Path
logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, str(Path(__file__).parent))

from config import CONFIG

film_hash = "68d303a1fbd4"
out_dir = Path("generated") / film_hash

story = json.loads((out_dir / "story.json").read_text())
images = json.loads((out_dir / "images.json").read_text())
vb = json.loads((out_dir / "visual_bible.json").read_text())

char_map = images.get("character_map", {})
scenes = images.get("scenes", [])

L4_URL = CONFIG.CLOUD_GPU_ENDPOINT + "/generate_clip"
DURATION = CONFIG.CLIP_DURATION_S

print(f"L4: {L4_URL}")
print(f"Film: {story['title']}")
print(f"Scenes: {len(scenes)}, Characters: {len(char_map)}")
print()

async def generate_clip(prompt, seed, ref_url=None):
    payload = {"prompt": prompt, "seed": seed, "duration_s": DURATION}
    if ref_url:
        payload["reference_image_url"] = ref_url
    async with httpx.AsyncClient(timeout=600) as c:
        try:
            r = await c.post(L4_URL, json=payload)
            if r.status_code == 200 and len(r.content) > 1000:
                return r.content
            print(f"  L4 failed: {r.status_code} ({len(r.content)}b)")
        except Exception as e:
            print(f"  L4 error: {e}")
    return None

async def main():
    clips = []
    ref_url = None
    for ch, portraits in char_map.items():
        if portraits:
            ref_url = portraits[0].get("url", "")
            break

    for i, scene in enumerate(scenes[:CONFIG.VIDEO_CLIP_COUNT]):
        if not isinstance(scene, dict):
            continue
        loc = scene.get("location", "ancient setting")
        summary = scene.get("summary", f"Scene {i+1}")
        prompt = f"A cinematic scene at {loc}. {summary}. Maya architecture, stone pyramids, starlit sky. Cinematic, photorealistic, 35mm wide shot, dramatic lighting."
        seed = abs(hash(f"{film_hash}_scene_{i}")) % 99999

        print(f"Scene {i+1}: {prompt[:80]}...")
        t0 = time.time()
        mp4 = await generate_clip(prompt, seed, ref_url)
        dt = time.time() - t0
        if mp4:
            path = out_dir / f"clip_{i+1}.mp4"
            path.write_bytes(mp4)
            clips.append({"scene_id": f"s{i}", "source": "cloud_gpu", "file": str(path),
                         "prompt": prompt, "seed": seed, "size_kb": len(mp4)/1024,
                         "time_s": dt})
            print(f"  OK: {len(mp4)/1024:.0f} KB in {dt:.0f}s → {path.name}")
        else:
            print(f"  FAIL in {dt:.0f}s")
        await asyncio.sleep(1)

    (out_dir / "l4_clips.json").write_text(json.dumps(clips, default=str, indent=2))
    print(f"\nDone: {len(clips)} real L4 video clips generated")

asyncio.run(main())
