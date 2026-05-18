import asyncio, sys, time, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from chain import generate_story, detect_mode
from schemas import StoryRequest
from schemas.enums import Culture, Timeline, Theme
from agents.director import DirectorAgent
from agents.production_designer import ProductionDesignerAgent
from schemas import WorkOrder
from utils.visual_engine import visual_engine
from image_agent import image_agent
from audio.edge_tts_service import edge_tts_service, get_voice_for_culture


async def run_combo(name, culture, timeline, theme, seed, label):
    print("=" * 80)
    print(f"  {label}: {name}")
    print("=" * 80)

    req = StoryRequest(seed_idea=seed, culture=culture, timeline=timeline, theme=theme)
    mode, bridge = detect_mode(culture.value, timeline.value)
    dist = bridge.get("distance_buckets", "?")
    print(f"  Mode: {mode} (dist={dist})")
    print()

    # STORY
    print("--- STORY ---")
    t0 = time.time()
    result = await generate_story(req)
    print(f"  Title: {result.title}")
    print(f"  Words: {len(result.story.split())}")
    print(f"  Stereotypes: {result.stereotypes_flagged}")
    print(f"  Seed OK: {result.validation_seed}  Theme OK: {result.validation_theme}")
    print(f"  Time: {time.time()-t0:.1f}s")
    print(f"  Preview: {result.story[:200]}...")
    print()

    story_hash = hashlib.sha256(
        f"{culture.value}|{timeline.value}|{theme.value}|{seed}".encode()
    ).hexdigest()[:16]

    # VISUAL BIBLE
    print("--- VISUAL BIBLE ---")
    t1 = time.time()
    ve = await visual_engine.get(culture.value, timeline.value)
    ve_total = sum(len(v) for v in ve.values() if isinstance(v, list))
    print(f"  VisualElementsEngine: {ve_total} items ({time.time()-t1:.1f}s)")

    wo = WorkOrder(agent_type="director", input_data={
        "title": result.title, "culture": culture.value, "timeline": timeline.value,
        "theme": theme.value, "story": result.story,
        "characters": result.characters,
        "scenes": [{"location": result.setting[:50], "summary": seed, "emotional_beat": "wonder_discovery"}],
        "visual_elements": ve,
    })
    agent = DirectorAgent()
    dr = await agent.execute(wo)
    vb_ok = dr.success
    chars = len(dr.output_data.get("character_bibles", [])) if dr.success else 0
    sig = len(dr.output_data.get("character_bibles", [{}])[0].get("signature_items", [])) if vb_ok and chars else 0
    shots = sum(len(v) for v in dr.output_data.get("shot_variation_matrix", {}).values()) if vb_ok else 0
    tone = dr.output_data.get("film_tone", "?")[:80] if vb_ok else "?"
    print(f"  Director: {'PASS' if vb_ok else 'FAIL'} | Tone: {tone}")
    print(f"  Characters: {chars} | Sig items: {sig} | Shots: {shots}")
    print()

    # IMAGES
    print("--- IMAGES ---")
    st_data = {
        "title": result.title, "setting": result.setting,
        "characters": result.characters, "story": result.story,
        "metadata": {
            "culture": culture.value, "timeline": timeline.value, "theme": theme.value,
            "culture_display": culture.value.replace("_", " ").title(),
            "timeline_display": timeline.value.replace("_", " ").title(),
            "theme_display": theme.value.capitalize(),
        }
    }
    t2 = time.time()
    img = await image_agent.generate_all_images(st_data, story_hash)
    setting_url = img["setting"]["url"] if img.get("setting") else None
    char_count = len(img.get("characters", []))
    print(f"  Setting: {'GENERATED' if setting_url else 'FAILED'}")
    if setting_url:
        print(f"    URL: {setting_url[:100]}...")
    print(f"  Characters: {char_count} portraits")
    for ch in img.get("characters", [])[:3]:
        print(f"    - {ch['character']}: {ch['url'][:80]}...")
    print(f"  Time: {time.time()-t2:.1f}s")
    print()

    # AUDIO
    print("--- AUDIO ---")
    t3 = time.time()
    voice = get_voice_for_culture(culture.value)
    audio = await edge_tts_service.generate(
        text=result.story[:500],
        voice=voice, rate="-10%",
    )
    audio_ok = audio is not None and len(audio) > 1000
    print(f"  Voice: {voice}")
    print(f"  Audio: {len(audio)} bytes ({'OK' if audio_ok else 'FAILED'})")
    print(f"  Time: {time.time()-t3:.1f}s")
    print()

    return {
        "title": result.title,
        "words": len(result.story.split()),
        "mode": mode, "distance": dist,
        "story_ok": result.validation_seed and result.validation_theme,
        "flags": len(result.stereotypes_flagged),
        "ve_elements": ve_total,
        "vb_ok": vb_ok, "chars": chars, "sig": sig, "shots": shots,
        "images_ok": setting_url is not None,
        "char_images": char_count,
        "audio_ok": audio_ok, "audio_bytes": len(audio) if audio else 0,
        "tone": tone,
        "preview": result.story[:120],
    }


async def main():
    r1 = await run_combo(
        "Viking Blacksmith", Culture.VIKING, Timeline.HIGH_MEDIEVAL, Theme.AMBITION,
        "A blacksmith who forges a blade from fallen star metal must choose between wealth and protecting his daughter",
        "COMBO 1"
    )
    print()
    print()
    r2 = await run_combo(
        "Nazi Resistance", Culture.NAZI_GERMANY, Timeline.COLD_WAR, Theme.SURVIVAL,
        "A young woman in divided Berlin hides forbidden books in a bakery basement while the Stasi closes in",
        "COMBO 2"
    )

    print()
    print("=" * 80)
    print("  FULL PIPELINE AUDIT — RESULTS")
    print("=" * 80)
    for i, r in enumerate([r1, r2]):
        print(f"\n  Combo {i+1}: {r['title']}")
        print(f"    Story:    {r['words']}w, mode={r['mode']}(dist={r['distance']}), flags={r['flags']}, seed+theme={'OK' if r['story_ok'] else 'FAIL'}")
        print(f"    VB:       {r['ve_elements']}el, {r['chars']}chars, {r['sig']}sig, {r['shots']}shots, {'PASS' if r['vb_ok'] else 'FAIL'}")
        print(f"    Images:   {'PASS' if r['images_ok'] else 'FAIL'} (setting + {r['char_images']} portraits)")
        print(f"    Audio:    {'PASS' if r['audio_ok'] else 'FAIL'} ({r['audio_bytes']} bytes)")
        print(f"    Tone:     {r['tone']}")
        print(f"    Preview:  {r['preview']}...")

    all_pass = all([
        r1["story_ok"], r1["vb_ok"], r1["images_ok"], r1["audio_ok"],
        r2["story_ok"], r2["vb_ok"], r2["images_ok"], r2["audio_ok"],
    ])
    print(f"\n  ALL PIPELINE PHASES PASSED: {all_pass}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
