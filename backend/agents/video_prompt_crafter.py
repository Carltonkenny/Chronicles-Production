from agents.base_agent import BaseAgent
from schemas import WorkOrder, WorkResult
from prompts.video_prompt_crafter_prompt import (
    VIDEO_PROMPT_CRAFTER_PROMPT, CINEMATOGRAPHER_PERSONALITY
)
from utils.llm_client import call_llm
from config import CONFIG
from logger_config import setup_logger
import hashlib

logger = setup_logger("VideoPromptCrafter")


class VideoPromptCrafter(BaseAgent):
    agent_type = "video_prompt_crafter"

    async def _execute_internal(self, work_order: WorkOrder) -> WorkResult:
        data = work_order.input_data
        scene = data.get("scene", {})
        visual_bible = data.get("visual_bible", {})
        character_bibles = data.get("character_bibles", {})
        ref_images = data.get("reference_images", {})
        audio_prompts = data.get("audio_prompts", {})
        clip_duration = data.get("clip_duration", CONFIG.CLIP_DURATION_S)

        char_bibles_text = ""
        ref_images_text = ""
        if character_bibles:
            for name, cb in character_bibles.items():
                char_bibles_text += f"\n**{name}:** {cb.get('appearance', '')}"
                sigs = cb.get("signature_items", [])
                if sigs:
                    char_bibles_text += f" | Signature items: {', '.join(sigs)}"
                char_bibles_text += "\n"
        if ref_images:
            for name, url in ref_images.items():
                ref_images_text += f"- {name}: {url}\n"

        color_palette = visual_bible.get("color_palette", [])
        if isinstance(color_palette, list):
            color_palette = ", ".join(color_palette)

        prompt = VIDEO_PROMPT_CRAFTER_PROMPT.format(
            scene_id=scene.get("id", "unknown"),
            summary=scene.get("summary", ""),
            location=scene.get("location", ""),
            characters_present=str(scene.get("characters", [])),
            emotional_beat=scene.get("emotional_beat", "neutral"),
            target_duration_s=clip_duration,
            character_bibles=char_bibles_text or "None",
            reference_images=ref_images_text or "None",
            color_palette=color_palette or "Not specified",
            lighting_style=visual_bible.get("lighting_style", "Natural"),
            camera_language=visual_bible.get("camera_language", "Standard"),
            architecture=visual_bible.get("architecture", ""),
            props=visual_bible.get("props", ""),
        )

        llm_result = await call_llm(
            system=CINEMATOGRAPHER_PERSONALITY,
            user=prompt,
            temperature=0.7,
            max_tokens=500,
        )

        video_prompt = llm_result.strip() if isinstance(llm_result, str) else ""
        if not video_prompt:
            video_prompt = (
                f"A cinematic scene at {scene.get('location', 'unknown')}. "
                f"{scene.get('summary', '')}"
            )

        self.tokens_used = 0

        character_anchors = []
        for name, cb in character_bibles.items():
            appearance = cb.get("appearance", "")
            sigs = cb.get("signature_items", [])
            if sigs:
                appearance += f" | Items: {', '.join(sigs)}"
            character_anchors.append(f"{name}: {appearance}")

        scene_id = scene.get("id", "unknown")

        ref_image_url = None
        image_list = []
        chars = scene.get("characters", [])
        for char_name in chars:
            if isinstance(char_name, str):
                url = ref_images.get(char_name)
                if url:
                    image_list.append({
                        "url": url, "frame_idx": 0, "strength": 1.0,
                        "character_name": char_name,
                    })
                    if ref_image_url is None:
                        ref_image_url = url

        scene_id_str = str(scene_id)
        audio_prompt = audio_prompts.get(scene_id_str, "")

        return WorkResult(
            success=True,
            output_data={
                "scene_id": scene_id_str,
                "video_prompt": video_prompt,
                "audio_prompt": audio_prompt,
                "reference_image_url": ref_image_url,
                "images": image_list,
                "seed": int(hashlib.sha256(f"{work_order.story_hash}_{scene_id_str}".encode()).hexdigest(), 16) % 99999,
                "expected_duration_s": clip_duration,
                "character_anchors": character_anchors,
            },
            wall_time_ms=self.wall_time_ms,
            tokens_used=self.tokens_used,
        )
