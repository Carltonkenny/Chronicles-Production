import asyncio
from typing import List

from config import CONFIG
from schemas import WorkOrder, WorkResult
from schemas.image_result import ImageResult
from agents.base_agent import BaseAgent
from image.image_api import ImageAPIClient, SETTING_QUALITY
from prompts.character_portrait_prompt import CHARACTER_PORTRAIT_PROMPT
from utils.llm_client import call_llm
from utils import get_visual_elements
from logger_config import setup_logger

logger = setup_logger("CharPortraitGen")

VARIATION_TYPES = ["full_body", "close_up", "action"]


class CharacterPortraitGen(BaseAgent):
    agent_type = "character_portrait_gen"

    def __init__(self, timeout_ms: int = None):
        super().__init__(timeout_ms)
        self._api = ImageAPIClient()

    async def _execute_internal(self, work_order: WorkOrder) -> WorkResult:
        data = work_order.input_data
        char_bible = data.get("character_bible", {})
        culture = data.get("culture", "")
        timeline = data.get("timeline", "")
        theme = data.get("theme", "")
        story_hash = work_order.story_hash or "unknown"
        vb = data.get("visual_bible", {})

        name = char_bible.get("name", "Unknown")
        role = char_bible.get("role", "")
        appearance = char_bible.get("appearance", "")
        costume = char_bible.get("costume", "")
        sig_items = ", ".join(char_bible.get("signature_items", []))
        emotional_range = char_bible.get("emotional_range", "")
        color_palette = vb.get("color_palette", {})
        palette_str = f"Primary: {', '.join(color_palette.get('primary', []))}. "
        palette_str += f"Accent: {', '.join(color_palette.get('accent', []))}"

        results = []
        for vtype in VARIATION_TYPES:
            prompt = CHARACTER_PORTRAIT_PROMPT.format(
                name=name,
                role=role,
                appearance=appearance,
                costume=costume,
                signature_items=sig_items or "None specified",
                emotional_range=emotional_range or "Neutral",
                culture=culture,
                timeline=timeline,
                theme=theme,
                film_tone=vb.get("film_tone", ""),
                color_palette=palette_str,
                lighting_style=vb.get("lighting_style", ""),
                variation_type=vtype,
            )
            try:
                system = "You are a character portrait designer. Output ONLY the visual description, no markdown."
                description = await call_llm(
                    system=system,
                    user=prompt,
                    max_tokens=300,
                    temperature=0.6,
                    task="portrait",
                )
                description = description.strip().strip('"').strip("'")
            except (RuntimeError, asyncio.TimeoutError) as e:
                logger.warning(f"LLM failed for {name}/{vtype}: {e}")
                description = f"{appearance[:200]}, {costume[:100]}, {sig_items[:100]}"
                if not description.strip():
                    description = f"A {culture} {role} wearing {costume}"

            visual_elements = get_visual_elements(culture, timeline)
            db_clothing = ""
            if visual_elements.get("clothing"):
                c = visual_elements["clothing"][0]
                mats = ", ".join(c.get("materials", [])[:2])
                colors = ", ".join(c.get("colors", [])[:2])
                db_clothing = f"{c['description']} ({mats}, {colors})"
            if db_clothing:
                description += f", {db_clothing}"

            quality = f"{SETTING_QUALITY}, {theme} mood"
            base_prompt = f"{description}, {culture} {timeline} era, {quality}"

            variant_data = await self._api.build_portrait_urls(
                story_hash=story_hash,
                character_name=name,
                base_prompt=base_prompt,
                variations=1,
            )
            for vd in variant_data:
                results.append(ImageResult(
                    url=vd["url"],
                    prompt=vd["prompt"],
                    seed=vd["seed"],
                    variation=vtype,
                    orientation=vd["orientation"],
                    character=name,
                    source="generated",
                ))

        self.tokens_used = len(results) * 150
        logger.info(f"[{self.agent_type}] Generated {len(results)} portraits for {name}")
        return WorkResult(
            success=True,
            output_data={
                "character": name,
                "portraits": [r.model_dump() for r in results],
            },
            wall_time_ms=self.wall_time_ms,
            tokens_used=self.tokens_used,
        )
