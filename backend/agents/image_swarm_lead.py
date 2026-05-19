import asyncio
import time

from typing import List

from config import CONFIG
from schemas import WorkOrder, WorkResult
from schemas.image_result import ImageResult, ImageOutput
from agents.base_agent import BaseAgent
from agents.character_portrait_gen import CharacterPortraitGen
from agents.scene_keyframe_gen import SceneKeyframeGen
from image.image_api import ImageAPIClient
from logger_config import setup_logger

logger = setup_logger("ImageSwarmLead")


class ImageSwarmLead(BaseAgent):
    agent_type = "image_swarm_lead"

    def __init__(self, timeout_ms: int = None):
        super().__init__(timeout_ms or 60000)
        self._api = ImageAPIClient()

    async def _execute_internal(self, work_order: WorkOrder) -> WorkResult:
        data = work_order.input_data
        story_hash = work_order.story_hash or "unknown"
        characters = data.get("characters", [])
        scenes = data.get("scenes", [])
        culture = data.get("culture", "")
        timeline = data.get("timeline", "")
        theme = data.get("theme", "")
        vb = data.get("visual_bible", {})
        char_bibles = vb.get("character_bibles", [])
        location_descriptions = vb.get("location_descriptions", [])

        start = time.time()

        portrait_tasks = []
        for cb in char_bibles:
            if not isinstance(cb, dict):
                continue
            portrait_wo = WorkOrder(
                agent_type="character_portrait_gen",
                input_data={
                    "character_bible": cb,
                    "culture": culture,
                    "timeline": timeline,
                    "theme": theme,
                    "visual_bible": vb,
                },
                story_hash=story_hash,
                priority=2,
            )
            agent = CharacterPortraitGen(timeout_ms=30000)
            portrait_tasks.append(agent.execute(portrait_wo))

        scene_tasks = []
        for scene in scenes:
            if not isinstance(scene, dict):
                continue
            scene_wo = WorkOrder(
                agent_type="scene_keyframe_gen",
                input_data={
                    "scene": scene,
                    "culture": culture,
                    "timeline": timeline,
                    "theme": theme,
                    "visual_bible": vb,
                },
                story_hash=story_hash,
                priority=2,
            )
            agent = SceneKeyframeGen(timeout_ms=30000)
            scene_tasks.append(agent.execute(scene_wo))

        logger.info(
            f"[{self.agent_type}] Spawning {len(portrait_tasks)} portrait + "
            f"{len(scene_tasks)} scene agents in parallel"
        )

        sem = asyncio.Semaphore(CONFIG.MAX_CONCURRENT_LLM)
        async def run_with_semaphore(task):
            async with sem:
                return await task

        all_portrait = await asyncio.gather(
            *[run_with_semaphore(t) for t in portrait_tasks],
            return_exceptions=True,
        )
        all_scene = await asyncio.gather(
            *[run_with_semaphore(t) for t in scene_tasks],
            return_exceptions=True,
        )

        portrait_results: List[ImageResult] = []
        for r in all_portrait:
            if isinstance(r, WorkResult) and r.success:
                char_portraits = r.output_data.get("portraits", [])
                for p in char_portraits:
                    portrait_results.append(ImageResult(**p))
            elif isinstance(r, Exception):
                logger.warning(f"Portrait agent failed: {r}")

        scene_results: List[ImageResult] = []
        for r in all_scene:
            if isinstance(r, WorkResult) and r.success:
                kf = r.output_data.get("keyframe", {})
                if kf:
                    scene_results.append(ImageResult(**kf))
            elif isinstance(r, Exception):
                logger.warning(f"Scene agent failed: {r}")

        wall = (time.time() - start) * 1000

        char_map = {}
        for r in portrait_results:
            char = r.character or "unknown"
            if char not in char_map:
                char_map[char] = []
            char_map[char].append(r.model_dump())

        output = ImageOutput(
            story_hash=story_hash,
            portraits=portrait_results,
            scenes=scene_results,
            total_count=len(portrait_results) + len(scene_results),
            wall_time_ms=wall,
            character_map=char_map,
        )

        logger.info(
            f"[{self.agent_type}] Complete: {len(portrait_results)} portraits + "
            f"{len(scene_results)} scenes in {wall:.0f}ms"
        )

        self.tokens_used = sum(
            r.tokens_used for r in all_portrait + all_scene
            if isinstance(r, WorkResult)
        )

        return WorkResult(
            success=True,
            output_data=output.model_dump(),
            wall_time_ms=wall,
            tokens_used=self.tokens_used,
        )
