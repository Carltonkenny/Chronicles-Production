from typing import Dict, Any

from agents.base_agent import BaseAgent
from schemas import WorkOrder, WorkResult
from prompts.colorist_prompt import COLORIST_PROMPT
from utils.llm_client import call_llm
from logger_config import setup_logger

logger = setup_logger("ColoristAgent")


class ColoristAgent(BaseAgent):
    agent_type = "colorist"

    async def _execute_internal(self, work_order: WorkOrder) -> WorkResult:
        data = work_order.input_data
        color_palette = data.get("color_palette", "")
        lighting_style = data.get("lighting_style", "")
        emotional_arc = data.get("emotional_arc", "")
        scene_count = data.get("scene_count", 6)

        prompt = COLORIST_PROMPT.format(
            color_palette=color_palette or "Not specified",
            lighting_style=lighting_style or "Natural",
            emotional_arc=emotional_arc or "Neutral",
            scene_count=scene_count,
        )

        llm_result = await call_llm(
            system=COLORIST_PROMPT.split("## INPUT")[0],
            user=prompt,
            temperature=0.3,
            max_tokens=500,
            task="default",
        )

        self.tokens_used = 0

        import json as _json
        grading_spec = {}
        try:
            if isinstance(llm_result, str):
                text = llm_result.strip()
                if text.startswith("```"):
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                grading_spec = _json.loads(text)
        except (_json.JSONDecodeError, AttributeError):
            grading_spec = {
                "base_grade": {
                    "brightness": 0.0,
                    "contrast": 1.05,
                    "saturation": 0.95,
                    "temperature_offset": 0.0,
                    "vignette": 0.0,
                },
                "scene_adjustments": [],
            }

        logger.info(f"[{self.agent_type}] Grading spec: contrast={grading_spec.get('base_grade', {}).get('contrast', '?')}")

        return WorkResult(
            success=True,
            output_data={
                "grading_spec": grading_spec,
            },
            wall_time_ms=self.wall_time_ms,
            tokens_used=self.tokens_used,
        )
