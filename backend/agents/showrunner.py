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
            "story",
            "complete",
            66,
            f"Story ready: {story_data.get('title', 'Untitled')} ({len(story_data.get('story', '').split())} words, {len(scenes_data.get('scenes', []))} scenes)",
        )

        combined = {
            "story": story_data,
            "blueprint": blueprint.output_data if blueprint.success else {},
            "scenes": scenes_data,
            "mode": bridge.get("mode", "historical") if bridge else "historical",
        }

        yield ProgressEvent("done", "story_complete", 66, "Story pipeline complete — handing off to production", combined)
