import json
from .base_agent import BaseAgent
from schemas import WorkOrder, WorkResult
from prompts.director_prompt import DIRECTOR_PROMPT
from utils.llm_client import call_llm
from utils import extract_and_repair_json
from logger_config import setup_logger

logger = setup_logger("DirectorAgent")


class DirectorAgent(BaseAgent):
    agent_type = "director"

    async def _execute_internal(self, work_order: WorkOrder) -> WorkResult:
        data = work_order.input_data
        title = data.get("title", "")
        culture = data.get("culture", "")
        timeline = data.get("timeline", "")
        theme = data.get("theme", "")
        story = data.get("story", "")
        characters = data.get("characters", [])
        scenes = data.get("scenes", [])
        visual_elements = data.get("visual_elements", {})

        if not story:
            return WorkResult(success=False, output_data={}, error_message="No story text", wall_time_ms=0, tokens_used=0)

        char_list = "\n".join(f"- {c}" for c in characters) if characters else "- No characters"
        scene_list = json.dumps(scenes[:12], indent=2) if scenes else "[]"
        ve_summary = json.dumps({k: len(v) for k, v in visual_elements.items()}) if visual_elements else "{}"

        user_msg = DIRECTOR_PROMPT.format(
            title=title, culture=culture, timeline=timeline, theme=theme,
            story=story, characters=char_list, scenes=scene_list,
            visual_elements=ve_summary,
        )

        try:
            raw = await call_llm(
                system="You are a film director. Output ONLY valid JSON. No commentary.",
                user=user_msg, max_tokens=3500, temperature=0.6, task="default"
            )
        except Exception as e:
            logger.error(f"Director LLM call failed: {e}")
            return WorkResult(success=False, output_data={}, error_message=str(e), wall_time_ms=self.wall_time_ms, tokens_used=0)

        bible = extract_and_repair_json(raw)
        logger.info(f"Director: Visual Bible created — {len(bible.get('character_bibles', []))} characters, {len(bible.get('location_descriptions', []))} locations")

        return WorkResult(success=True, output_data=bible, wall_time_ms=self.wall_time_ms, tokens_used=self.tokens_used)
