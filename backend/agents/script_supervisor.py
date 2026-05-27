import json
import hashlib
from .base_agent import BaseAgent
from schemas import WorkOrder, WorkResult
from prompts.script_supervisor_prompt import SCRIPT_SUPERVISOR_PROMPT
from utils import extract_and_repair_json
from utils.llm_client import call_llm
from config import CONFIG
from logger_config import setup_logger

logger = setup_logger("ScriptSupervisorAgent")


class ScriptSupervisorAgent(BaseAgent):
    agent_type = "script_supervisor"

    async def _execute_internal(self, work_order: WorkOrder) -> WorkResult:
        story_data = work_order.input_data
        title = story_data.get("title", "Untitled")
        setting = story_data.get("setting", "")
        characters = story_data.get("characters", [])
        theme = story_data.get("theme", "")
        story_text = story_data.get("story", "")
        wiki_context = story_data.get("wiki_context", "")

        if not story_text:
            logger.warning("No story text provided to Script Supervisor")
            return WorkResult(
                success=False,
                output_data={"scenes": []},
                error_message="No story text in input_data",
                wall_time_ms=0,
                tokens_used=0,
            )

        char_list = "\n".join(f"- {c}" for c in characters) if characters else "- No characters"
        theme_str = theme if isinstance(theme, str) else theme.value if hasattr(theme, "value") else str(theme)

        user_msg = SCRIPT_SUPERVISOR_PROMPT.format(
            title=title,
            setting=setting,
            characters=char_list,
            theme=theme_str,
            story=story_text,
        )

        if wiki_context:
            user_msg += f"\n\nHistorical Context:\n{wiki_context[:1000]}"

        system_msg = "You are a film industry script supervisor. Output ONLY valid JSON. No commentary."

        try:
            raw = await call_llm(
                system=system_msg,
                user=user_msg,
                max_tokens=2500,
                temperature=0.4,
                task="supervisor",
            )
        except Exception as e:
            logger.error(f"Script Supervisor LLM call failed: {e}")
            return WorkResult(
                success=False,
                output_data={"scenes": []},
                error_message=str(e),
                wall_time_ms=self.wall_time_ms,
                tokens_used=0,
            )

        scene_data = extract_and_repair_json(raw)
        scenes = scene_data.get("scenes", [])
        total = scene_data.get("total_scenes", len(scenes))
        duration = scene_data.get("estimated_total_duration_s", sum(s.get("target_duration_s", 8) for s in scenes))

        logger.info(
            f"Script Supervisor: {len(scenes)} scenes (target {total}), "
            f"estimated {duration}s total, "
            f"beats: {[s.get('emotional_beat', '?') for s in scenes]}"
        )

        output = {
            "scenes": scenes,
            "total_scenes": total,
            "estimated_total_duration_s": duration,
            "pacing_notes": scene_data.get("pacing_notes", ""),
        }

        blueprint_hash = hashlib.sha256(json.dumps(output, sort_keys=True).encode()).hexdigest()[:8]
        logger.info(f"Scene breakdown hash: {blueprint_hash}")

        return WorkResult(
            success=True,
            output_data=output,
            wall_time_ms=self.wall_time_ms,
            tokens_used=self.tokens_used,
        )
