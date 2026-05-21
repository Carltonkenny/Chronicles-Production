"""
Full pipeline runner — generates a complete film end-to-end.
Usage: python pipeline_runner.py <culture> <timeline> <theme> <seed_idea>
Saves everything to generated/<story_hash>/
"""
import sys, asyncio, time, json, hashlib, logging
from pathlib import Path

logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, str(Path(__file__).parent))

from chain import generate_story, detect_mode
from schemas import StoryRequest, WorkOrder
from schemas.enums import Culture, Timeline, Theme
from agents.director import DirectorAgent
from agents.image_swarm_lead import ImageSwarmLead
from agents.video_lead import VideoLead
from agents.editor import EditorAgent
from agents.sound_designer import SoundDesignerAgent
from agents.colorist import ColoristAgent
from post.assembler import FFmpegAssembler
from config import CONFIG

OUTPUT_BASE = Path(__file__).parent / "generated"


async def run_film(label: str, culture: Culture, timeline: Timeline, theme: Theme, seed: str):
    t0 = time.time()
    story_hash = hashlib.sha256(
        f"{culture.value}|{timeline.value}|{theme.value}|{seed}".encode()
    ).hexdigest()[:12]

    out_dir = OUTPUT_BASE / f"{story_hash}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"FILM: {label}")
    print(f"Hash: {story_hash}")
    print(f"Combo: {culture.value} x {timeline.value} x {theme.value}")
    print(f"{'='*60}")

    results = {"label": label, "hash": story_hash, "seed": seed,
               "culture": culture.value, "timeline": timeline.value, "theme": theme.value}

    # Phase 1: Story
    print("\n[Phase 1] Generating story via Groq...")
    t1 = time.time()
    mode, bridge = detect_mode(culture.value, timeline.value)
    dist = bridge.get("distance_buckets", "?") if bridge else "?"
    req = StoryRequest(seed_idea=seed, culture=culture, timeline=timeline, theme=theme)
    story_result = await generate_story(req)
    story_time = time.time() - t1
    words = len(story_result.story.split())
    print(f"  Title: {story_result.title}")
    print(f"  Words: {words} | Mode: {mode} dist={dist} | Time: {story_time:.0f}s")

    story_json = {
        "title": story_result.title, "setting": story_result.setting,
        "characters": story_result.characters, "story": story_result.story,
        "theme_reflection": story_result.theme_reflection,
        "stereotypes_flagged": story_result.stereotypes_flagged,
        "validation_seed": story_result.validation_seed,
        "validation_theme": story_result.validation_theme,
        "word_count": words, "mode": mode, "distance": str(dist),
        "generation_time_s": story_time,
    }
    (out_dir / "story.json").write_text(json.dumps(story_json, indent=2))
    results["story"] = story_result.title
    results["words"] = words
    results["mode"] = mode

    # Print story for user to read
    print(f"\n  STORY PREVIEW:")
    print(f"  {'='*50}")
    for line in story_result.story[:600].split("\n"):
        print(f"  {line}")
    print(f"  ...")
    print(f"  Full story saved to: {out_dir / 'story.json'}")

    # Rate limit: wait before next heavy LLM call
    await asyncio.sleep(5)

    # Phase 2: Visual Bible
    print("\n[Phase 2] Visual Bible...")
    dir_agent = DirectorAgent()
    dir_wo = WorkOrder(agent_type="director", input_data={
        "title": story_result.title, "culture": culture.value,
        "timeline": timeline.value, "theme": theme.value,
        "story": story_result.story, "characters": story_result.characters,
        "scenes": [], "visual_elements": {},
    }, story_hash=story_hash, priority=1)
    dir_result = await dir_agent.execute(dir_wo)
    vb = dir_result.output_data if dir_result.success else {}
    print(f"  Director: {'OK' if dir_result.success else 'FAIL'}")
    (out_dir / "visual_bible.json").write_text(json.dumps(vb, default=str, indent=2))
    await asyncio.sleep(5)

    # Phase 3: Image Swarm
    print("\n[Phase 3] Image Swarm (Pollinations)...")
    char_list = [c for c in story_result.characters if c.strip()]
    img_agent = ImageSwarmLead()
    img_wo = WorkOrder(agent_type="image_swarm_lead", input_data={
        "culture": culture.value, "timeline": timeline.value,
        "theme": theme.value, "characters": char_list,
        "scenes": [{"id": f"s{i}", "summary": f"Scene {i+1}", "location": "Unknown"} for i in range(CONFIG.VIDEO_CLIP_COUNT)],
        "visual_bible": vb,
    }, story_hash=story_hash, priority=1)
    img_result = await img_agent.execute(img_wo)
    img_data = img_result.output_data if img_result.success else {}
    total_imgs = img_data.get("total_count", 0)
    print(f"  Images: {'OK' if img_result.success else 'FAIL'} ({total_imgs} generated)")
    (out_dir / "images.json").write_text(json.dumps(img_data, default=str, indent=2))
    results["images"] = total_imgs
    await asyncio.sleep(3)

    # Phase 4: Video Swarm (L4 GPU)
    print("\n[Phase 4] Video Swarm (L4 GPU)...")
    scenes_for_video = []
    scene_list = img_data.get("scenes", []) if img_data else []
    for i in range(CONFIG.VIDEO_CLIP_COUNT):
        if i < len(scene_list):
            scenes_for_video.append(scene_list[i] if isinstance(scene_list[i], dict) else {"id": f"s{i}", "summary": f"Scene {i+1}"})
        elif scene_list:
            scenes_for_video.append(scene_list[i % len(scene_list)] if isinstance(scene_list[i % len(scene_list)], dict) else {"id": f"s{i}", "summary": f"Scene {i+1}"})

    char_bibles = vb.get("character_bibles", []) if vb else []
    char_bibles_dict = {}
    for cb in char_bibles:
        if isinstance(cb, dict) and "name" in cb:
            char_bibles_dict[cb["name"]] = cb

    ref_images = {}
    char_map = img_data.get("character_map", {}) if img_data else {}
    for ch_name, portraits_list in char_map.items():
        if portraits_list and len(portraits_list) > 0:
            ref_images[ch_name] = portraits_list[0].get("url", "")

    video_agent = VideoLead()
    video_wo = WorkOrder(agent_type="video_lead", input_data={
        "scenes": scenes_for_video, "visual_bible": vb,
        "character_bibles": char_bibles_dict, "reference_images": ref_images,
        "clip_duration": CONFIG.CLIP_DURATION_S,
    }, story_hash=story_hash, priority=1)
    video_result = await video_agent.execute(video_wo)
    clips = video_result.output_data.get("clips", []) if video_result.success else []
    print(f"  Video: {'OK' if video_result.success else 'FAIL'} ({len(clips)} clips)")
    (out_dir / "video_clips.json").write_text(json.dumps(clips, default=str, indent=2))
    results["clips"] = len(clips)

    # Phase 5: Post-Production
    print("\n[Phase 5] Post-Production (Editor + Sound + Colorist + Assembly)...")

    scenes_for_editor = [{"id": f"s{i}", "summary": f"Scene {i+1}", "location": "Unknown",
                          "characters": char_list[:2], "emotional_beat": "wonder"} for i in range(CONFIG.VIDEO_CLIP_COUNT)]

    editor = EditorAgent()
    ed_wo = WorkOrder(agent_type="editor", input_data={
        "title": story_result.title, "culture": culture.value,
        "timeline": timeline.value, "theme": theme.value,
        "scenes": scenes_for_editor, "clip_data": clips,
        "target_duration_s": CONFIG.TARGET_FILM_DURATION_S,
    }, story_hash=story_hash, priority=1)
    ed_result = await editor.execute(ed_wo)
    assembly = ed_result.output_data.get("assembly_timeline", {}) if ed_result.success else {}
    print(f"  Editor: {'OK' if ed_result.success else 'FAIL'}")

    sound = SoundDesignerAgent()
    sd_wo = WorkOrder(agent_type="sound_designer", input_data={
        "narration_path": f"/tmp/narration_{story_hash}.mp3",
        "culture": culture.value, "scenes": scenes_for_editor,
    }, story_hash=story_hash, priority=2)
    sd_result = await sound.execute(sd_wo)
    audio = sd_result.output_data.get("audio_timeline", {}) if sd_result.success else {}
    print(f"  Sound: {'OK' if sd_result.success else 'FAIL'}")

    colorist = ColoristAgent()
    col_wo = WorkOrder(agent_type="colorist", input_data={
        "color_palette": vb.get("color_palette", "#D4451A") if vb else "#D4451A",
        "lighting_style": vb.get("lighting_style", "Natural") if vb else "Natural",
        "emotional_arc": "wonder to resolution",
        "scene_count": CONFIG.VIDEO_CLIP_COUNT,
    }, story_hash=story_hash, priority=2)
    col_result = await colorist.execute(col_wo)
    grading = col_result.output_data.get("grading_spec", {}) if col_result.success else {}
    print(f"  Colorist: {'OK' if col_result.success else 'FAIL'}")

    post_data = {"editor": assembly, "sound": audio, "colorist": grading}
    (out_dir / "assembly.json").write_text(json.dumps(post_data, default=str, indent=2))

    print("\n[Assembly] FFmpeg...")
    assembler = FFmpegAssembler(output_dir=out_dir)
    mp4_path = assembler.assemble(
        story_hash=story_hash, assembly_timeline=assembly,
        audio_timeline=audio, grading_spec=grading, clip_data=clips,
    )
    if mp4_path and mp4_path.exists():
        size_kb = mp4_path.stat().st_size / 1024
        print(f"  MP4 created: {size_kb:.1f} KB ({mp4_path})")
        results["mp4"] = str(mp4_path)
    else:
        print(f"  MP4 not created (FFmpeg missing or no clips)")

    total_time = time.time() - t0
    results["total_time_s"] = total_time
    print(f"\n{'='*60}")
    print(f"FILM COMPLETE: {story_result.title}")
    print(f"Total time: {total_time:.0f}s")
    print(f"Output: {out_dir}")
    print(f"{'='*60}\n")

    return results


async def main():
    if len(sys.argv) == 5:
        culture_enum = Culture(sys.argv[1])
        timeline_enum = Timeline(sys.argv[2])
        theme_enum = Theme(sys.argv[3])
        seed_idea = sys.argv[4]
        label = f"{culture_enum.value} x {timeline_enum.value} x {theme_enum.value}"
        await run_film(label, culture_enum, timeline_enum, theme_enum, seed_idea)
    else:
        films = [
            ("Maya x Interplanetary Frontier x Discovery",
             Culture.MAYA, Timeline.INTERPLANETARY_FRONTIER, Theme.DISCOVERY,
             "A Maya astronomer discovers a star map encoded in ancient pyramids that predicts the collapse of digital civilization"),
            ("Nazi Germany x Classical Antiquity x Betrayal",
             Culture.NAZI_GERMANY, Timeline.CLASSICAL_ANTIQUITY, Theme.BETRAYAL,
             "An archaeologist discovers a Roman legion that adopted Nazi ideology and built a secret underground empire"),
            ("Yoruba x Climate Migration x Identity",
             Culture.YORUBA, Timeline.CLIMATE_MIGRATION, Theme.IDENTITY,
             "A Yoruba ocean engineer in Lagos builds floating cities for climate refugees while discovering her grandmother was an Ogboni secret keeper"),
            ("Chola x AI Hegemony x Obsession",
             Culture.CHOLA, Timeline.AI_HEGEMONY, Theme.OBSESSION,
             "A temple sculptor programs AI drones to carve a kilometer-high statue of Shiva from a Himalayan peak"),
            ("Viking x Systemic Collapse x Survival",
             Culture.VIKING, Timeline.SYSTEMIC_COLLAPSE, Theme.SURVIVAL,
             "A Norse fishing village survives the collapse of global civilization by rediscovering runic technology"),
        ]
        for label, c, tl, th, seed in films:
            print(f"\n{'#'*60}")
            print(f"# STARTING: {label}")
            print(f"{'#'*60}")
            await run_film(label, c, tl, th, seed)
            print(f"\n{'#'*60}")
            print(f"# WAITING 60s for Groq rate limit reset...")
            print(f"{'#'*60}")
            await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
