from agents.base_agent import BaseAgent
from schemas import WorkOrder, WorkResult
from utils.llm_client import call_llm
from logger_config import setup_logger

logger = setup_logger("CharacterDesigner")

CHARACTER_DESIGN_SYSTEM = """You are a character designer for a historical/fantasy film studio.
For the given character, produce an exhaustive physical specification including height,
weight, body type, skin tone, hair, eyes, distinguishing features, and a detailed visual
description suitable for a character turnaround model sheet.

Output ONLY valid JSON. No markdown, no explanations."""

CHARACTER_DESIGN_PROMPT = """## CHARACTER
Name: {name}
Role: {role}
Appearance (from bible): {appearance}
Costume (from bible): {costume}
Signature Items: {signature_items}

## WORLD CONTEXT
Culture: {culture}
Timeline: {timeline}
Theme: {theme}
Film Tone: {film_tone}
Color Palette: {color_palette}

## YOUR TASK
Produce a complete physical design document for this character. Be specific and era-appropriate.

For the TURNAROUND_IMAGE_PROMPT field: describe a character model sheet showing 4 views side-by-side:
- LEFT: front standing pose, full body, neutral expression, arms slightly away from body, height scale bar on left in feet and metric
- CENTER-LEFT: back view, full body, hair and costume back details visible
- CENTER-RIGHT: profile/side view, posture and silhouette
- RIGHT: signature action pose that captures personality
All on a studio gray backdrop. Professional character reference model sheet, even lighting, photorealistic 8K.

Output JSON:
{{
  "height_cm": 175,
  "weight_kg": 80,
  "body_type": "muscular, broad-shouldered",
  "skin_tone": "weathered, olive complexion #C4A882",
  "hair_color": "dark brown #3B2F2F",
  "hair_style": "shoulder-length, braided at temples",
  "eye_color": "hazel #8B7355",
  "face_shape": "angular, strong jawline",
  "build": "warrior's build — broad chest, scarred forearms",
  "distinguishing_features": "notched left ear, ritual scar across chest, missing tip of right pinky",
  "voice_traits": "gravelly baritone, speaks slowly, Icelandic accent",
  "turnaround_image_prompt": "Character model sheet showing 4 views... [200 words]"
}}

## RULES
- Height MUST be era-appropriate: Romans average 165-170cm, Vikings 170-175cm, modern 170-180cm
- Weight MUST reflect build and era nutrition levels
- Colors MUST be from the provided color palette where possible
- Distinguishing features should connect to the character's role and theme
- The turnaround_image_prompt is the SINGLE most important output — this is the identity seed for all subsequent images
"""


class CharacterDesignerAgent(BaseAgent):
    agent_type = "character_designer"

    async def _execute_internal(self, work_order: WorkOrder) -> WorkResult:
        data = work_order.input_data
        char_bible = data.get("character_bible", {})
        culture = data.get("culture", "")
        timeline = data.get("timeline", "")
        theme = data.get("theme", "")
        vb = data.get("visual_bible", {})

        name = char_bible.get("name", "Unknown")
        role = char_bible.get("role", "")
        appearance = char_bible.get("appearance", "")
        costume = char_bible.get("costume", "")
        sig_items = ", ".join(char_bible.get("signature_items", []))
        film_tone = vb.get("film_tone", "")
        color_palette = vb.get("color_palette", {})

        palette_str = ""
        if isinstance(color_palette, dict):
            palette_str = f"Primary: {', '.join(color_palette.get('primary', []))}. "
            palette_str += f"Accent: {', '.join(color_palette.get('accent', []))}"

        prompt = CHARACTER_DESIGN_PROMPT.format(
            name=name,
            role=role,
            appearance=appearance,
            costume=costume,
            signature_items=sig_items or "None specified",
            culture=culture,
            timeline=timeline,
            theme=theme,
            film_tone=film_tone,
            color_palette=palette_str,
        )

        import json as _json
        try:
            llm_result = await call_llm(
                system=CHARACTER_DESIGN_SYSTEM,
                user=prompt,
                temperature=0.5,
                max_tokens=1200,
                task="default",
            )
            text = llm_result.strip() if isinstance(llm_result, str) else "{}"
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            design = _json.loads(text)
        except (RuntimeError, _json.JSONDecodeError) as e:
            logger.warning(f"LLM failed for {name} design: {e}")
            design = {
                "height_cm": 170,
                "weight_kg": 70,
                "body_type": "average",
                "skin_tone": "natural",
                "hair_color": "brown",
                "hair_style": "period-appropriate",
                "eye_color": "brown",
                "face_shape": "oval",
                "build": "average",
                "distinguishing_features": "",
                "voice_traits": "neutral",
                "turnaround_image_prompt": f"{appearance[:200]}. {costume[:100]}. Character reference model sheet with front, back, side, and action poses on studio gray backdrop. {culture} {timeline} era. Photorealistic character turnaround sheet.",
            }

        logger.info(f"[{self.agent_type}] Designed {name}: {design.get('height_cm')}cm, {design.get('body_type')}")

        return WorkResult(
            success=True,
            output_data={
                "character": name,
                "design": design,
                "turnaround_prompt": design.get("turnaround_image_prompt", ""),
            },
            wall_time_ms=self.wall_time_ms,
            tokens_used=800,
        )
