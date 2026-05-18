import json
from .base_agent import BaseAgent
from schemas import WorkOrder, WorkResult
from prompts.production_designer_prompt import PRODUCTION_DESIGNER_PROMPT
from utils.llm_client import call_llm
from utils import extract_and_repair_json
from utils.visual_engine import visual_engine
from logger_config import setup_logger

logger = setup_logger("ProductionDesignerAgent")


class ProductionDesignerAgent(BaseAgent):
    agent_type = "production_designer"

    async def _execute_internal(self, work_order: WorkOrder) -> WorkResult:
        data = work_order.input_data
        culture = data.get("culture", "")
        timeline = data.get("timeline", "")
        theme = data.get("theme", "")
        setting = data.get("setting", "")
        characters = data.get("characters", [])
        locations = data.get("locations", [])

        logger.info(f"PD: Loading visual elements for {culture}/{timeline}")
        ve_data = await visual_engine.get(culture, timeline)

        char_list = "\n".join(f"- {c}" for c in characters) if characters else "- No characters"
        loc_list = "\n".join(f"- {l}" for l in locations) if locations else "- No locations"
        ve_formatted = json.dumps(ve_data, indent=2, default=str) if ve_data else "{}"

        user_msg = PRODUCTION_DESIGNER_PROMPT.format(
            culture=culture, timeline=timeline, theme=theme,
            setting=setting, characters=char_list, locations=loc_list,
            visual_elements=ve_formatted,
        )

        try:
            raw = await call_llm(
                system="You are a film production designer. Output ONLY valid JSON. No commentary.",
                user=user_msg, max_tokens=3000, temperature=0.5, task="default"
            )
        except Exception as e:
            logger.error(f"PD LLM call failed: {e}")
            return WorkResult(success=False, output_data={}, error_message=str(e), wall_time_ms=self.wall_time_ms, tokens_used=0)

        pd_output = extract_and_repair_json(raw)
        logger.info(f"PD: World built — {len(pd_output.get('locations', []))} locations, {len(pd_output.get('material_inventory', []))} materials")

        return WorkResult(success=True, output_data=pd_output, wall_time_ms=self.wall_time_ms, tokens_used=self.tokens_used)
