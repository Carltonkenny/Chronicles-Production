from typing import Dict, Any
from .base_agent import BaseAgent
from schemas import WorkOrder, WorkResult
from config import CONFIG
from utils.llm_client import call_llm
from utils.json_repair import extract_and_repair_json
from prompts import STORY_PLANNER_PROMPT, LLM_OUTPUT_INSTRUCTION, get_culture_traps
from utils.stereotype_scan import get_culture_traps
from logger_config import setup_logger

logger = setup_logger("PlannerAgent")


class PlannerAgent(BaseAgent):
    agent_type = "planner"

    async def _execute_internal(self, work_order: WorkOrder) -> WorkResult:
        culture = work_order.input_data.get("culture")
        timeline = work_order.input_data.get("timeline")
        theme = work_order.input_data.get("theme")
        seed_idea = work_order.input_data.get("seed_idea")
        wiki_context = work_order.input_data.get("wiki_context", "")

        user_msg = STORY_PLANNER_PROMPT.format(
            culture=culture,
            timeline=timeline,
            theme=theme,
            seed_idea=seed_idea,
            wiki_context=wiki_context,
            culture_traps=get_culture_traps(culture),
        )

        logger.info(f"Generating blueprint for {culture}/{timeline}/{theme}")

        raw = await call_llm(
            system=f"{LLM_OUTPUT_INSTRUCTION}",
            user=user_msg,
            max_tokens=CONFIG.PLANNER_MAX_TOKENS,
            temperature=CONFIG.PLANNER_TEMPERATURE,
        )

        blueprint = extract_and_repair_json(raw)
        self.tokens_used = len(raw.split())

        logger.info(f"Blueprint ready: {blueprint.get('title', 'Untitled')}")

        return WorkResult(
            success=True,
            output_data={"blueprint": blueprint},
            wall_time_ms=self.wall_time_ms,
            tokens_used=self.tokens_used
        )
