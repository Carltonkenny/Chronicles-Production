import asyncio
import time

from typing import List

from config import CONFIG
from schemas import WorkOrder, WorkResult
from schemas.image_result import ImageResult, PropImageResult, ImageOutput
from agents.base_agent import BaseAgent
from agents.character_designer import CharacterDesignerAgent
from agents.character_portrait_gen import CharacterPortraitGen
from agents.scene_keyframe_gen import SceneKeyframeGen
from agents.prop_designer import PropDesignerAgent
from agents.prop_image_gen import PropImageGenAgent
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
        char_bibles = (
            vb.get("director", {}).get("character_bibles")
            or vb.get("character_bibles", [])
        )
        if not char_bibles and characters:
            logger.info(f"[{self.agent_type}] No character_bibles in VB, building from story characters ({len(characters)} found)")
            char_bibles = []
            for char_str in characters:
                if isinstance(char_str, str) and ':' in char_str:
                    name, desc = char_str.split(':', 1)
                    char_bibles.append({
                        "name": name.strip(),
                        "appearance": desc.strip()[:300],
                        "costume": "",
                        "signature_items": [],
                        "emotional_range": "",
                    })
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

        design_tasks = []
        for cb in char_bibles:
            if not isinstance(cb, dict):
                continue
            design_wo = WorkOrder(
                agent_type="character_designer",
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
            agent = CharacterDesignerAgent(timeout_ms=30000)
            design_tasks.append(agent.execute(design_wo))

        prop_wo = WorkOrder(
            agent_type="prop_designer",
            input_data={
                "culture": culture,
                "timeline": timeline,
                "visual_bible": vb,
            },
            story_hash=story_hash,
            priority=3,
        )
        prop_designer = PropDesignerAgent()
        prop_task = prop_designer.execute(prop_wo)

        all_design = await asyncio.gather(
            *[run_with_semaphore(t) for t in design_tasks],
            return_exceptions=True,
        )

        prop_result = await run_with_semaphore(prop_task)

        all_portrait = await asyncio.gather(
            *[run_with_semaphore(t) for t in portrait_tasks],
            return_exceptions=True,
        )
        all_scene = await asyncio.gather(
            *[run_with_semaphore(t) for t in scene_tasks],
            return_exceptions=True,
        )

        design_results: List[ImageResult] = []
        for r in all_design:
            if isinstance(r, WorkResult) and r.success:
                tp = r.output_data.get("turnaround_prompt", "")
                char = r.output_data.get("character", "unknown")
                if tp:
                    turn_data = await self._api.build_turnaround_url(story_hash, char, tp)
                    design_results.append(ImageResult(
                        url=turn_data["url"],
                        prompt=turn_data["prompt"],
                        seed=turn_data["seed"],
                        variation="turnaround_sheet",
                        orientation="landscape",
                        character=char,
                        source="generated",
                    ))
                design = r.output_data.get("design", {})
                char_sheet_prompt = design.get("turnaround_image_prompt", tp)
                if char_sheet_prompt:
                    sheet_data = await self._api.build_character_sheet_url(story_hash, char, char_sheet_prompt)
                    design_results.append(ImageResult(
                        url=sheet_data["url"],
                        prompt=sheet_data["prompt"],
                        seed=sheet_data["seed"],
                        variation="character_sheet",
                        orientation="square",
                        character=char,
                        source="generated",
                    ))
        portrait_results: List[ImageResult] = []
        for r in all_portrait:
            if isinstance(r, WorkResult) and r.success:
                char_portraits = r.output_data.get("portraits", [])
                for p in char_portraits:
                    portrait_results.append(ImageResult(**p))
            elif isinstance(r, Exception):
                logger.warning(f"Portrait agent failed: {r}")

        prop_results: List[PropImageResult] = []
        if isinstance(prop_result, WorkResult) and prop_result.success:
            extracted_props = prop_result.output_data.get("props", [])
            if extracted_props:
                prop_gen_wo = WorkOrder(
                    agent_type="prop_image_gen",
                    input_data={"props": extracted_props},
                    story_hash=story_hash,
                    priority=3,
                )
                prop_gen = PropImageGenAgent()
                gen_result = await run_with_semaphore(prop_gen.execute(prop_gen_wo))
                if isinstance(gen_result, WorkResult) and gen_result.success:
                    for pr in gen_result.output_data.get("prop_images", []):
                        prop_results.append(PropImageResult(**pr))
        elif isinstance(prop_result, Exception):
            logger.warning(f"Prop agent failed: {prop_result}")

        scene_results: List[ImageResult] = []
        for r in all_scene:
            if isinstance(r, WorkResult) and r.success:
                kfs = r.output_data.get("keyframes", [])
                if not kfs:
                    kf = r.output_data.get("keyframe", {})
                    if kf:
                        kfs = [kf]
                for kf in kfs:
                    scene_results.append(ImageResult(**kf))
            elif isinstance(r, Exception):
                logger.warning(f"Scene agent failed: {r}")

        wall = (time.time() - start) * 1000

        char_map = {}
        for r in portrait_results + design_results:
            char = r.character or "unknown"
            if char not in char_map:
                char_map[char] = []
            char_map[char].append(r.model_dump())

        output = ImageOutput(
            story_hash=story_hash,
            portraits=portrait_results,
            scenes=scene_results,
            props=prop_results,
            character_designs=design_results,
            total_count=len(portrait_results) + len(scene_results) + len(design_results) + len(prop_results),
            wall_time_ms=wall,
            character_map=char_map,
        )

        logger.info(
            f"[{self.agent_type}] Complete: {len(design_results)} designs + "
            f"{len(portrait_results)} portraits + {len(prop_results)} props + "
            f"{len(scene_results)} scenes in {wall:.0f}ms"
        )

        self.tokens_used = sum(
            r.tokens_used for r in all_design + all_portrait + all_scene
            if isinstance(r, WorkResult)
        )
        if isinstance(prop_result, WorkResult):
            self.tokens_used += prop_result.tokens_used

        return WorkResult(
            success=True,
            output_data=output.model_dump(),
            wall_time_ms=wall,
            tokens_used=self.tokens_used,
        )
