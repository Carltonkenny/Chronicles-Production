import json
from .base_agent import BaseAgent
from schemas import WorkOrder, WorkResult
from prompts.art_director_prompt import ART_DIRECTOR_PROMPT
from utils.llm_client import call_llm
from utils import extract_and_repair_json
from logger_config import setup_logger

logger = setup_logger("ArtDirectorAgent")


class ArtDirectorAgent(BaseAgent):
    agent_type = "art_director"

    async def _execute_internal(self, work_order: WorkOrder) -> WorkResult:
        data = work_order.input_data
        culture = data.get("culture", "")
        timeline = data.get("timeline", "")
        theme = data.get("theme", "")
        characters = data.get("characters", [])
        scenes = data.get("scenes", [])
        pd_output = data.get("pd_output", {})
        visual_elements = data.get("visual_elements", {})

        char_list = "\n".join(f"- {c}" for c in characters) if characters else "- No characters"
        scene_list = json.dumps(scenes[:12], indent=2) if scenes else "[]"
        pd_str = json.dumps(pd_output, indent=2, default=str) if pd_output else "{}"
        ve_str = json.dumps({k: len(v) for k, v in visual_elements.items()}) if visual_elements else "{}"

        user_msg = ART_DIRECTOR_PROMPT.format(
            culture=culture, timeline=timeline, theme=theme,
            characters=char_list, scenes=scene_list,
            pd_output=pd_str, visual_elements=ve_str,
        )

        try:
            raw = await call_llm(
                system="You are a film art director. Output ONLY valid JSON. No commentary.",
                user=user_msg, max_tokens=3000, temperature=0.5, task="default"
            )
        except Exception as e:
            logger.error(f"AD LLM call failed: {e}")
            return WorkResult(success=False, output_data={}, error_message=str(e), wall_time_ms=self.wall_time_ms, tokens_used=0)

        ad_output = extract_and_repair_json(raw)
        symbols = len(ad_output.get("cultural_symbols", []))
        logger.info(f"AD: Props + symbols ready — {symbols} cultural symbols, motif arc defined")

        return WorkResult(success=True, output_data=ad_output, wall_time_ms=self.wall_time_ms, tokens_used=self.tokens_used)
