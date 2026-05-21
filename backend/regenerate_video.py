"""Regenerate video for Film 1 using real L4 GPU."""
import sys, asyncio, json, time, logging
from pathlib import Path
logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, str(Path(__file__).parent))

from agents.video_lead import VideoLead
from agents.editor import EditorAgent
from agents.sound_designer import SoundDesignerAgent
from agents.colorist import ColoristAgent
from post.assembler import FFmpegAssembler
from schemas import WorkOrder
from config import CONFIG

film_hash = "68d303a1fbd4"
out_dir = Path("generated") / film_hash
story = json.loads((out_dir / "story.json").read_text())
images = json.loads((out_dir / "images.json").read_text())
vb = json.loads((out_dir / "visual_bible.json").read_text())

scenes_for_video = []
scene_list = images.get("scenes", [])
for i in range(CONFIG.VIDEO_CLIP_COUNT):
    if i < len(scene_list):
        s = scene_list[i]
        scenes_for_video.append(s if isinstance(s, dict) else {"id": f"s{i}"})
    elif scene_list:
        s = scene_list[i % len(scene_list)]
        scenes_for_video.append(s if isinstance(s, dict) else {"id": f"s{i}"})

char_bibles_dict = {}
for cb in vb.get("character_bibles", []):
    if isinstance(cb, dict) and "name" in cb:
        char_bibles_dict[cb["name"]] = cb

ref_images = {}
for ch, portraits in images.get("character_map", {}).items():
    if portraits:
        ref_images[ch] = portraits[0].get("url", "")


async def main():
    print("=" * 60)
    print(f"REGENERATING VIDEO: {story['title']}")
    print("=" * 60)
    print(f"L4 endpoint: {CONFIG.CLOUD_GPU_ENDPOINT}")
    print(f"Scenes: {len(scenes_for_video)}")
    print(f"Characters: {len(char_bibles_dict)}")
    print(f"Reference images: {len(ref_images)}")
    print()

    t0 = time.time()

    # Phase 4: Real video with L4 GPU
    print("[Phase 4] Video generation via L4 GPU...")
    video_agent = VideoLead()
    video_wo = WorkOrder(agent_type="video_lead", input_data={
        "scenes": scenes_for_video,
        "visual_bible": vb,
        "character_bibles": char_bibles_dict,
        "reference_images": ref_images,
        "clip_duration": CONFIG.CLIP_DURATION_S,
    }, story_hash=film_hash, priority=1)

    video_result = await video_agent.execute(video_wo)
    clips = video_result.output_data.get("clips", []) if video_result.success else []
    video_time = time.time() - t0

    real_clips = [c for c in clips if c.get("source") == "cloud_gpu"]
    print(f"Video: {len(clips)} clips total, {len(real_clips)} from L4 GPU, time={video_time:.0f}s")
    for c in clips:
        print(f"  {c.get('scene_id', '?'):12s} src={c.get('source', '?'):12s} qc={c.get('qc_status', '?'):8s}")

    (out_dir / "video_clips.json").write_text(json.dumps(clips, default=str, indent=2))

    if not real_clips:
        print("\nNo real L4 clips generated. Skipping post-production.")
        return

    # Phase 5: Post-production
    print("\n[Phase 5] Post-production...")
    char_list = story.get("characters", [])
    ed_scenes = [{"id": f"s{i}", "summary": f"Scene {i+1}",
                  "location": "Unknown", "characters": char_list[:2],
                  "emotional_beat": "wonder"} for i in range(CONFIG.VIDEO_CLIP_COUNT)]

    editor = EditorAgent()
    ed_result = await editor.execute(WorkOrder(agent_type="editor", input_data={
        "title": story["title"], "culture": story.get("culture", "maya"),
        "timeline": story.get("timeline", "interplanetary_frontier"),
        "theme": story.get("theme", "discovery"), "scenes": ed_scenes,
        "clip_data": clips, "target_duration_s": CONFIG.TARGET_FILM_DURATION_S,
    }, story_hash=film_hash, priority=1))
    assembly = ed_result.output_data.get("assembly_timeline", {}) if ed_result.success else {}
    print(f"  Editor: {'OK' if ed_result.success else 'FAIL'}")

    sound = SoundDesignerAgent()
    sd_result = await sound.execute(WorkOrder(agent_type="sound_designer", input_data={
        "narration_path": f"/tmp/narration_{film_hash}.mp3",
        "culture": story.get("culture", "maya"), "scenes": ed_scenes,
    }, story_hash=film_hash, priority=2))
    audio = sd_result.output_data.get("audio_timeline", {}) if sd_result.success else {}
    print(f"  Sound: {'OK' if sd_result.success else 'FAIL'}")

    colorist = ColoristAgent()
    col_result = await colorist.execute(WorkOrder(agent_type="colorist", input_data={
        "color_palette": vb.get("color_palette", ""),
        "lighting_style": vb.get("lighting_style", ""),
        "emotional_arc": "wonder to resolution",
        "scene_count": CONFIG.VIDEO_CLIP_COUNT,
    }, story_hash=film_hash, priority=2))
    grading = col_result.output_data.get("grading_spec", {}) if col_result.success else {}
    print(f"  Colorist: {'OK' if col_result.success else 'FAIL'}")

    (out_dir / "assembly.json").write_text(json.dumps(
        {"editor": assembly, "sound": audio, "colorist": grading}, default=str, indent=2))

    print("\n[Assembly] FFmpeg...")
    assembler = FFmpegAssembler(output_dir=out_dir)
    mp4_path = assembler.assemble(story_hash=film_hash, assembly_timeline=assembly,
                                  audio_timeline=audio, grading_spec=grading, clip_data=clips)

    total = time.time() - t0
    print("=" * 60)
    if mp4_path and mp4_path.exists():
        print(f"FILM COMPLETE: {mp4_path.stat().st_size/1024:.0f} KB")
        print(f"Path: {mp4_path}")
    else:
        print(f"MP4 not created (FFmpeg unavailable)")
    print(f"Total time: {total:.0f}s ({total//60}m {total%60:.0f}s)")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
