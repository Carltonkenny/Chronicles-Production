import asyncio

from config import CONFIG
from schemas import WorkOrder, WorkResult
from schemas.image_result import ImageResult
from agents.base_agent import BaseAgent
from image.image_api import ImageAPIClient, SETTING_QUALITY
from prompts.scene_image_prompt import SCENE_IMAGE_PROMPT
from utils.llm_client import call_llm
from utils import get_visual_elements
from logger_config import setup_logger

logger = setup_logger("SceneKeyframeGen")


class SceneKeyframeGen(BaseAgent):
    agent_type = "scene_keyframe_gen"

    def __init__(self, timeout_ms: int = None):
        super().__init__(timeout_ms)
        self._api = ImageAPIClient()

    async def _execute_internal(self, work_order: WorkOrder) -> WorkResult:
        data = work_order.input_data
        scene = data.get("scene", {})
        culture = data.get("culture", "")
        timeline = data.get("timeline", "")
        theme = data.get("theme", "")
        story_hash = work_order.story_hash or "unknown"
        vb = data.get("visual_bible", {})

        scene_id = scene.get("id", "unknown")
        summary = scene.get("summary", "")
        location = scene.get("location", "")
        characters = ", ".join(scene.get("characters", [])) or "None"
        emotional_beat = scene.get("emotional_beat", "")

        color_palette = vb.get("color_palette", {})
        palette_str = f"Primary: {', '.join(color_palette.get('primary', []))}. "
        palette_str += f"Accent: {', '.join(color_palette.get('accent', []))}"

        loc_data = {}
        for loc in vb.get("location_descriptions", []):
            if isinstance(loc, dict) and loc.get("name", "").lower() in location.lower():
                loc_data = loc
                break
            if isinstance(loc, dict) and loc.get("name", "").lower() == location.lower():
                loc_data = loc
                break

        architecture = ""
        materials_list = []
        lighting = loc_data.get("lighting", vb.get("lighting_style", ""))
        time_of_day = loc_data.get("time_of_day", "day")
        if loc_data:
            architecture = loc_data.get("description", "")[:200]
            materials_list = loc_data.get("materials", [])

        visual_elements = get_visual_elements(culture, timeline)
        if not architecture and visual_elements.get("architecture"):
            arch = visual_elements["architecture"][0]
            architecture = arch["description"]
            materials_list = arch.get("materials", [])

        prompt = SCENE_IMAGE_PROMPT.format(
            scene_id=scene_id,
            summary=summary[:200],
            location=location,
            characters=characters,
            emotional_beat=emotional_beat or theme,
            architecture=architecture or "Period-appropriate architecture",
            materials=", ".join(materials_list[:5]) or "Period materials",
            lighting=lighting or "Natural lighting",
            time_of_day=time_of_day,
            culture=culture,
            timeline=timeline,
            theme=theme,
            film_tone=vb.get("film_tone", ""),
            color_palette=palette_str,
            lighting_style=vb.get("lighting_style", ""),
        )

        try:
            system = "You are a film cinematographer. Output ONLY the scene visual description, no markdown."
            description = await call_llm(
                system=system,
                user=prompt,
                max_tokens=400,
                temperature=0.6,
                task="scene",
            )
            description = description.strip().strip('"').strip("'")
        except (RuntimeError, asyncio.TimeoutError) as e:
            logger.warning(f"LLM failed for scene {scene_id}: {e}")
            description = f"{summary}. Location: {location}. {vb.get('film_tone', '')} atmosphere, {theme} mood"

        full_prompt = f"{description}, {culture} {timeline} era, {theme} mood, {SETTING_QUALITY}"

        scene_data_list = await self._api.build_scene_variation_urls(
            story_hash=story_hash,
            scene_id=scene_id,
            base_prompt=full_prompt,
        )

        results = []
        for sd in scene_data_list:
            results.append(ImageResult(
                url=sd["url"],
                prompt=sd["prompt"],
                seed=sd["seed"],
                variation=sd["variation"],
                orientation="landscape",
                scene_id=scene_id,
                source="generated",
            ))

        self.tokens_used = 200
        logger.info(f"[{self.agent_type}] Generated {len(results)} keyframes for scene {scene_id}")
        return WorkResult(
            success=True,
            output_data={
                "scene_id": scene_id,
                "keyframes": [r.model_dump() for r in results],
                "keyframe": results[0].model_dump(),
            },
            wall_time_ms=self.wall_time_ms,
            tokens_used=self.tokens_used,
        )
