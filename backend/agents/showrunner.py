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
    data: dict
    error: bool

    def __init__(self, phase: str, step: str, pct: int, message: str, data: dict | None = None, error: bool = False):
        self.phase = phase
        self.step = step
        self.pct = pct
        self.message = message
        self.data = data or {}
        self.error = error

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "step": self.step,
            "pct": self.pct,
            "message": self.message,
            "data": self.data,
            "error": self.error,
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
        story_hash: str = "",
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
                story_hash=story_hash,
            )
            blueprint = await planner_fn(planner_work_order)
        except Exception as e:
            logger.error(f"Planner failed: {e}")
            yield ProgressEvent("story", "planning", 0, f"Planner failed: {e}")
            return

        yield ProgressEvent("story", "writing_scenes", 25, "Writing narrative and breaking scenes...")

        try:
            writer_scene_work_order = WorkOrder(
                agent_type="writer_scene",
                input_data={
                    "blueprint": blueprint.output_data if blueprint.success else {},
                    "seed_idea": story_request.seed_idea,
                    "culture": story_request.culture.value,
                    "timeline": story_request.timeline.value,
                    "theme": story_request.theme.value,
                    "wiki_context": wiki_context,
                },
                story_hash=story_hash,
            )
            story_result = await writer_fn(writer_scene_work_order)
        except Exception as e:
            logger.error(f"WriterScene failed: {e}")
            yield ProgressEvent("story", "writing_scenes", 25, f"WriterScene failed: {e}")
            return

        story_data = story_result.output_data if story_result.success else {"story": "", "scenes": [], "dialogues": {}}
        scenes_data = {"scenes": story_data.get("scenes", [])}

        yield ProgressEvent(
            "story", "complete", 50,
            f"Story ready: {story_data.get('title', 'Untitled')} ({len(story_data.get('story', '').split())} words, {len(scenes_data.get('scenes', []))} scenes)",
            story_data,
        )

        yield ProgressEvent("visual_bible", "architect", 55, "Creating visual bible...")

        visual_bible = {}
        try:
            vba_work_order = WorkOrder(
                agent_type="visual_bible_architect",
                input_data={
                    "title": story_data.get("title", ""),
                    "culture": story_request.culture.value,
                    "timeline": story_request.timeline.value,
                    "theme": story_request.theme.value,
                    "story": story_data.get("story", ""),
                    "characters": story_data.get("characters", []),
                    "scenes": scenes_data.get("scenes", []),
                },
                story_hash=story_hash,
            )
            vba_result = await director_fn(vba_work_order)
            if vba_result.success:
                visual_bible = vba_result.output_data
        except Exception as e:
            logger.error(f"VisualBibleArchitect failed: {e}")

        if visual_bible:
            yield ProgressEvent(
                "visual_bible", "complete", 66,
                f"Visual Bible ready", visual_bible,
            )

        image_output = None
        if image_swarm_fn:
            yield ProgressEvent(
                "images", "swarming", 68,
                "Spawning image swarm for characters, props, and scenes...",
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
                    story_hash=story_hash,
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

        yield ProgressEvent("pipeline_complete", "story_complete", 85, "All phases complete — final assembly", combined)
