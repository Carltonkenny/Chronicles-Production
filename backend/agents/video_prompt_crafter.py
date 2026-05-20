from agents.base_agent import BaseAgent
from schemas import WorkOrder, WorkResult
from prompts.video_prompt_crafter_prompt import (
    VIDEO_PROMPT_CRAFTER_PROMPT, CINEMATOGRAPHER_PERSONALITY
)
from utils.llm_client import call_llm
from config import CONFIG
from logger_config import setup_logger

logger = setup_logger("VideoPromptCrafter")


class VideoPromptCrafter(BaseAgent):
    agent_type = "video_prompt_crafter"

    async def _execute_internal(self, work_order: WorkOrder) -> WorkResult:
        data = work_order.input_data
        scene = data.get("scene", {})
        visual_bible = data.get("visual_bible", {})
        character_bibles = data.get("character_bibles", {})
        reference_images = data.get("reference_images", {})
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
        if reference_images:
            for name, url in reference_images.items():
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

        ref_image_url = None
        chars = scene.get("characters", [])
        if chars and len(chars) > 0:
            first_char = chars[0] if isinstance(chars[0], str) else ""
            ref_image_url = reference_images.get(first_char)

        return WorkResult(
            success=True,
            output_data={
                "scene_id": scene.get("id", "unknown"),
                "video_prompt": video_prompt,
                "reference_image_url": ref_image_url,
                "seed": abs(hash(f"{work_order.story_hash}_{scene.get('id', '')}")) % 99999,
                "expected_duration_s": clip_duration,
                "character_anchors": character_anchors,
            },
            wall_time_ms=self.wall_time_ms,
            tokens_used=self.tokens_used,
        )
