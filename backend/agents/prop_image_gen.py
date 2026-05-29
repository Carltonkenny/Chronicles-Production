import asyncio
from typing import List

from agents.base_agent import BaseAgent
from schemas import WorkOrder, WorkResult
from schemas.image_result import PropImageResult
from image.image_api import ImageAPIClient
from prompts.prop_image_prompt import format_prop_prompt, PROP_IMAGE_SYSTEM
from utils.llm_client import call_llm
from logger_config import setup_logger

logger = setup_logger("PropImageGen")

PROP_IMAGE_WIDTH = 768
PROP_IMAGE_HEIGHT = 768


class PropImageGenAgent(BaseAgent):
    agent_type = "prop_image_gen"

    def __init__(self, timeout_ms: int = None):
        super().__init__(timeout_ms or 60000)
        self._api = ImageAPIClient()

    async def _execute_internal(self, work_order: WorkOrder) -> WorkResult:
        data = work_order.input_data
        story_hash = work_order.story_hash or "unknown"
        props = data.get("props", [])

        results: List[PropImageResult] = []

        for prop in props[:40]:
            if not isinstance(prop, dict):
                continue
            prop_name = prop.get("name", "Unknown")
            prop_type = prop.get("prop_type", "accessory")
            materials = prop.get("materials", [])
            colors = prop.get("colors", [])
            era = prop.get("era_name", "")
            sig = prop.get("cultural_significance", "")
            owner = prop.get("character_owner")

            prompt = format_prop_prompt(prop_name, prop_type, materials, colors, era, sig)

            try:
                description = await call_llm(
                    system=PROP_IMAGE_SYSTEM,
                    user=prompt,
                    temperature=0.4,
                    max_tokens=200,
                    task="default",
                )
                description = description.strip().strip('"').strip("'")
            except (RuntimeError, asyncio.TimeoutError):
                mats_text = f"Crafted from {', '.join(materials)}." if materials else ""
                colors_text = f"Colors: {', '.join(colors)}." if colors else ""
                description = f"Isolated {prop_name} on neutral gray background. {mats_text} {colors_text} {era} era artifact. Studio lighting, sharp focus, 8K product photography."

            name_slug = prop_name.lower().replace(" ", "_")[:30]
            suffix = f"_prop_{name_slug}"
            seed = self._api.compute_seed(story_hash, suffix)

            final_prompt = f"{description}, {era} era artifact"
            url = self._api.build_image_url(final_prompt, seed, "square")

            results.append(PropImageResult(
                url=url,
                prompt=final_prompt,
                seed=seed,
                prop_name=prop_name,
                prop_type=prop_type,
                materials=materials,
                character_owner=owner,
                source="generated",
            ))

        self.tokens_used = len(results) * 150
        logger.info(f"[{self.agent_type}] Generated {len(results)} prop images")
        return WorkResult(
            success=True,
            output_data={"prop_images": [r.model_dump() for r in results]},
            wall_time_ms=self.wall_time_ms,
            tokens_used=self.tokens_used,
        )
