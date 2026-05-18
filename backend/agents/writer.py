from typing import Dict, Any
from .base_agent import BaseAgent
from schemas import WorkOrder, WorkResult
from config import CONFIG
from utils.llm_client import call_llm
from utils.json_repair import extract_and_repair_json
from prompts import STORY_WRITER_PROMPT, LLM_OUTPUT_INSTRUCTION
from logger_config import setup_logger
import json

logger = setup_logger("WriterAgent")


class WriterAgent(BaseAgent):
    agent_type = "writer"

    async def _execute_internal(self, work_order: WorkOrder) -> WorkResult:
        blueprint = work_order.input_data.get("blueprint")
        culture = work_order.input_data.get("culture")
        timeline = work_order.input_data.get("timeline")
        theme = work_order.input_data.get("theme")
        seed_idea = work_order.input_data.get("seed_idea")
        wiki_context = work_order.input_data.get("wiki_context", "")

        blueprint_chars = blueprint.get('supporting_characters', [])
        blueprint_chars_str = '\n'.join(f"- {char}" for char in blueprint_chars) if blueprint_chars else "No characters specified"

        user_msg = STORY_WRITER_PROMPT.format(
            seed_idea=seed_idea,
            blueprint=json.dumps(blueprint, indent=2),
            blueprint_characters=blueprint_chars_str,
            culture=culture,
            timeline=timeline,
            theme=theme,
            wiki_context=wiki_context,
        )

        logger.info(f"Generating narrative for {blueprint.get('title', 'Untitled')}")

        raw = await call_llm(
            system=f"{LLM_OUTPUT_INSTRUCTION}",
            user=user_msg,
            max_tokens=CONFIG.WRITER_MAX_TOKENS,
            temperature=CONFIG.WRITER_TEMPERATURE,
        )

        story_data = extract_and_repair_json(raw)
        self.tokens_used = len(raw.split())
        word_count = len(story_data.get("story", "").split())

        logger.info(f"Story ready: {word_count} words")

        return WorkResult(
            success=True,
            output_data={"story_data": story_data, "word_count": word_count},
            wall_time_ms=self.wall_time_ms,
            tokens_used=self.tokens_used
        )
