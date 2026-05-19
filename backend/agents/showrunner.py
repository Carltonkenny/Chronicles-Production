import asyncio
from typing import AsyncGenerator, Any

from .base_agent import BaseAgent
from schemas import WorkOrder, WorkResult
from logger_config import setup_logger

logger = setup_logger("ShowrunnerAgent")


class ProgressEvent:
    phase: str
    step: str
    pct: int
    message: str
    data: dict | None

    def __init__(self, phase: str, step: str, pct: int, message: str, data: dict | None = None):
        self.phase = phase
        self.step = step
        self.pct = pct
        self.message = message
        self.data = data or {}

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "step": self.step,
            "pct": self.pct,
            "message": self.message,
            "data": self.data,
        }


class ShowrunnerAgent(BaseAgent):
    agent_type = "showrunner"

    async def _execute_internal(self, work_order: WorkOrder) -> WorkResult:
        logger.info("Showrunner: full pipeline orchestration not available via _execute_internal")
        return WorkResult(
            success=True,
            output_data={"status": "pipeline_initiated"},
            wall_time_ms=self.wall_time_ms,
            tokens_used=self.tokens_used,
        )

    async def orchestrate(
        self,
        planner_fn,
        writer_fn,
        supervisor_fn,
        story_request: Any,
        wiki_context: str,
        bridge: dict | None = None,
        director_fn=None,
        pd_fn=None,
        ad_fn=None,
        image_swarm_fn=None,
    ) -> AsyncGenerator[ProgressEvent, None]:
        yield ProgressEvent("story", "planning", 0, "Creating story blueprint...")
        logger.info("Showrunner: Phase 1 — Planner")

        try:
            planner_work_order = WorkOrder(
                agent_type="planner",
                input_data={
                    "culture": story_request.culture.value,
                    "timeline": story_request.timeline.value,
                    "theme": story_request.theme.value,
                    "seed_idea": story_request.seed_idea,
                    "wiki_context": wiki_context,
                    "bridge": bridge,
                },
                story_hash=getattr(story_request, "seed_idea", "unknown"),
            )
            blueprint = await planner_fn(planner_work_order)
        except Exception as e:
            logger.error(f"Planner failed: {e}")
            yield ProgressEvent("story", "planning", 0, f"Planner failed: {e}")
            return

        yield ProgressEvent("story", "writing", 25, "Writing narrative...")

        try:
            writer_work_order = WorkOrder(
                agent_type="writer",
                input_data={
                    "blueprint": blueprint.output_data if blueprint.success else {},
                    "seed_idea": story_request.seed_idea,
                    "culture": story_request.culture.value,
                    "timeline": story_request.timeline.value,
                    "theme": story_request.theme.value,
                    "wiki_context": wiki_context,
                    "bridge": bridge,
                },
                story_hash=getattr(story_request, "seed_idea", "unknown"),
            )
            story_result = await writer_fn(writer_work_order)
        except Exception as e:
            logger.error(f"Writer failed: {e}")
            yield ProgressEvent("story", "writing", 25, f"Writer failed: {e}")
            return

        yield ProgressEvent("story", "supervising", 50, "Breaking down scenes...")

        try:
            story_data = story_result.output_data if story_result.success else {}
            supervisor_work_order = WorkOrder(
                agent_type="script_supervisor",
                input_data={
                    "title": story_data.get("title", ""),
                    "setting": story_data.get("setting", ""),
                    "characters": story_data.get("characters", []),
                    "theme": story_request.theme.value,
                    "story": story_data.get("story", ""),
                    "wiki_context": wiki_context,
                },
                story_hash=getattr(story_request, "seed_idea", "unknown"),
            )
            scene_result = await supervisor_fn(supervisor_work_order)
        except Exception as e:
            logger.error(f"Script Supervisor failed: {e}")
            yield ProgressEvent("story", "supervising", 50, f"Supervisor failed: {e}")
            return

        scenes_data = scene_result.output_data if scene_result.success else {"scenes": []}

        yield ProgressEvent(
            "story", "complete", 50,
            f"Story ready: {story_data.get('title', 'Untitled')} ({len(story_data.get('story', '').split())} words, {len(scenes_data.get('scenes', []))} scenes)",
        )

        visual_bible = {}
        if director_fn:
            yield ProgressEvent("visual_bible", "director", 55, "Creating visual vision...")

            try:
                director_work_order = WorkOrder(
                    agent_type="director",
                    input_data={
                        "title": story_data.get("title", ""),
                        "culture": story_request.culture.value,
                        "timeline": story_request.timeline.value,
                        "theme": story_request.theme.value,
                        "story": story_data.get("story", ""),
                        "characters": story_data.get("characters", []),
                        "scenes": scenes_data.get("scenes", []),
                        "visual_elements": visual_bible.get("visual_elements", {}),
                    },
                    story_hash=getattr(story_request, "seed_idea", "unknown"),
                )
                director_result = await director_fn(director_work_order)
                if director_result.success:
                    visual_bible["director"] = director_result.output_data
            except Exception as e:
                logger.error(f"Director failed: {e}")

        if pd_fn and "director" in visual_bible:
            yield ProgressEvent("visual_bible", "production_design", 58, "Building world...")

            try:
                locations = [s.get("location", "") for s in scenes_data.get("scenes", [])]
                pd_work_order = WorkOrder(
                    agent_type="production_designer",
                    input_data={
                        "culture": story_request.culture.value,
                        "timeline": story_request.timeline.value,
                        "theme": story_request.theme.value,
                        "setting": story_data.get("setting", ""),
                        "characters": story_data.get("characters", []),
                        "locations": list(set(locations)),
                    },
                    story_hash=getattr(story_request, "seed_idea", "unknown"),
                )
                pd_result = await pd_fn(pd_work_order)
                if pd_result.success:
                    visual_bible["production_designer"] = pd_result.output_data
            except Exception as e:
                logger.error(f"PD failed: {e}")

        if ad_fn and "production_designer" in visual_bible:
            yield ProgressEvent("visual_bible", "art_director", 61, "Designing props and symbols...")

            try:
                from utils.visual_engine import visual_engine
                ve_data = await visual_engine.get(story_request.culture.value, story_request.timeline.value)
                ad_work_order = WorkOrder(
                    agent_type="art_director",
                    input_data={
                        "culture": story_request.culture.value,
                        "timeline": story_request.timeline.value,
                        "theme": story_request.theme.value,
                        "characters": story_data.get("characters", []),
                        "scenes": scenes_data.get("scenes", []),
                        "pd_output": visual_bible.get("production_designer", {}),
                        "visual_elements": ve_data,
                    },
                    story_hash=getattr(story_request, "seed_idea", "unknown"),
                )
                ad_result = await ad_fn(ad_work_order)
                if ad_result.success:
                    visual_bible["art_director"] = ad_result.output_data
            except Exception as e:
                logger.error(f"AD failed: {e}")

        vb_agents = sum(1 for k in ["director", "production_designer", "art_director"] if k in visual_bible)
        if vb_agents > 0:
            yield ProgressEvent(
                "visual_bible", "complete", 66,
                f"Visual Bible ready ({vb_agents} agents)", visual_bible,
            )

        image_output = None
        if image_swarm_fn:
            yield ProgressEvent(
                "images", "swarming", 68,
                "Spawning image swarm for characters and scenes...",
            )

            try:
                image_work_order = WorkOrder(
                    agent_type="image_swarm_lead",
                    input_data={
                        "culture": story_request.culture.value,
                        "timeline": story_request.timeline.value,
                        "theme": story_request.theme.value,
                        "characters": story_data.get("characters", []),
                        "scenes": scenes_data.get("scenes", []),
                        "visual_bible": visual_bible,
                    },
                    story_hash=getattr(story_request, "seed_idea", "unknown"),
                )
                image_result = await image_swarm_fn(image_work_order)
                if image_result.success:
                    image_output = image_result.output_data
                    total = image_output.get("total_count", 0)
                    yield ProgressEvent(
                        "images", "complete", 85,
                        f"Image swarm complete: {total} images generated",
                        image_output,
                    )
            except Exception as e:
                logger.error(f"Image swarm failed: {e}")
                yield ProgressEvent("images", "failed", 85, f"Image swarm failed: {e}")

        combined = {
            "story": story_data,
            "blueprint": blueprint.output_data if blueprint.success else {},
            "scenes": scenes_data,
            "visual_bible": visual_bible,
            "images": image_output or {},
            "mode": bridge.get("mode", "historical") if bridge else "historical",
        }

        yield ProgressEvent("done", "story_complete", 85, "All phases complete — final assembly", combined)
