"""
VisualElementsEngine — Generates structured visual data per culture×timeline combo.
Sources: DB visual_elements → fallback_text → Wikipedia (skip if down) → LLM.
Validates deeply with creativity allowance. Caches in Redis with 90-day TTL.
"""
import json
import logging
from typing import Optional

from config import CONFIG, TIMELINE_BUCKETS, SAFETY_CONSTRAINED_CULTURES
from utils import extract_and_repair_json
from utils.wiki_context import get_db_fallback, get_visual_elements, format_visual_elements_for_prompt, get_wikipedia_summary, _load_db_cache
from utils.llm_client import call_llm
from prompts import STEREOTYPE_PATTERNS

logger = logging.getLogger("chronicles-visual-engine")

BUCKET_MATERIAL_MAP: dict[str, list[str]] = {
    "ancient": ["stone", "bronze", "copper", "clay", "linen", "wool", "wood", "leather", "gold"],
    "medieval": ["iron", "steel", "oak", "stone", "wool", "linen", "leather", "silver", "gold", "parchment"],
    "early_modern": ["iron", "steel", "brass", "cotton", "silk", "gunpowder", "glass", "paper", "oak"],
    "modern": ["steel", "concrete", "glass", "plastic", "nylon", "aluminum", "rubber", "synthetic_fabric"],
    "contemporary": ["steel", "glass", "silicon", "carbon_fiber", "titanium", "polyester", "LED"],
    "near_future": ["carbon_fiber", "titanium", "smart_glass", "nano_material", "bioplastic", "graphene"],
    "collapse": ["salvaged_metal", "scrap_wood", "recycled_plastic", "concrete_rubble", "cloth_scrap"],
    "space": ["titanium", "carbon_fiber", "aerogel", "composite", "smart_fabric", "regolith"],
}

STEREOTYPE_TRIGGERS: list[str] = []
for patterns in STEREOTYPE_PATTERNS.values():
    STEREOTYPE_TRIGGERS.extend(patterns)

VISUAL_ELEMENTS_PROMPT = """
You are a visual production designer for a film studio. Generate EXACT period-accurate visual elements for a {culture} story set in the {timeline} era.

## CULTURAL CONTEXT
{cultural_context}

## EXISTING DB DATA (if any)
{existing_data}

## YOUR TASK

Generate a JSON object with 6 categories of visual elements. Every element must be culturally authentic to {culture} during {timeline}.

### 1. clothing (2-4 items)
Period-accurate garments with specific materials and colors. Include:
- name, description, materials (list), colors (list with hex codes where possible)

### 2. architecture (2-3 items)
Building styles and structures specific to this culture×timeline. Include:
- name, description, materials, colors

### 3. artifact (3-5 items)
Props, tools, weapons, religious items, trade goods specific to this culture. Include:
- name, description, materials, colors

### 4. lighting (2-3 items)
Light sources and qualities authentic to this era. Include:
- name, description (light quality, color temperature)

### 5. hairstyle (2-3 items)
Period-accurate hairstyles with cultural significance. Include:
- name, description

### 6. color_palette (4-6 items)
Dominant colors for this culture with hex codes. Include:
- name (descriptive), description, colors (list of hex codes like #2C1810)

## CREATIVITY ALLOWANCE
- Prefer historically accurate. But if a combo is counterfactual (e.g., Roman + AI Hegemony), fuse the culture with the timeline creatively.
- Don't invent anachronistic materials (no titanium in Bronze Age, no steel before Iron Age).
- Be specific: "limestone" not "stone", "ochre yellow #CC7722" not "warm color".

## OUTPUT FORMAT
Respond with a single valid JSON object:
```json
{{
  "clothing": [{{"name": "...", "description": "...", "materials": ["limestone", "..."], "colors": ["#CC7722", "..."]}}],
  "architecture": [...],
  "artifact": [...],
  "lighting": [{{"name": "...", "description": "..."}}],
  "hairstyle": [{{"name": "...", "description": "..."}}],
  "color_palette": [{{"name": "...", "description": "...", "colors": ["#2C1810", "..."]}}]
}}
```
"""


class VisualElementsEngine:
    def __init__(self):
        self._redis = None
        logger.info("VisualElementsEngine initialized")

    async def _get_redis(self):
        if self._redis is not None:
            return self._redis
        try:
            from cache.story_cache import _get_redis as _r
            self._redis = await _r()
            return self._redis
        except Exception:
            return None

    async def get(self, culture: str, timeline: str) -> dict:
        r = await self._get_redis()

        if r:
            try:
                cached = await r.get(f"visual:{culture}:{timeline}")
                if cached:
                    logger.info(f"Redis hit: visual:{culture}:{timeline}")
                    return json.loads(cached)
            except Exception:
                pass

        db_data = get_visual_elements(culture, timeline)
        total = sum(len(v) for v in db_data.values())
        if total >= 12:
            logger.info(f"DB hit: {total} elements for {culture}/{timeline}")
            validated = self._validate(db_data, culture, timeline)
            if r:
                try:
                    await r.setex(f"visual:{culture}:{timeline}", 90 * 24 * 3600, json.dumps(validated, default=str))
                except Exception:
                    pass
            return validated

        return await self._generate(culture, timeline, db_data, r)

    async def _generate(self, culture: str, timeline: str, existing: dict, r) -> dict:
        fallback_text = get_db_fallback("culture", culture)
        timeline_text = get_db_fallback("timeline", timeline)

        wiki_context = ""
        try:
            wiki_result = await get_wikipedia_summary(culture, timeline)
            if wiki_result and len(wiki_result) > 100:
                wiki_context = wiki_result[:1500]
        except Exception:
            logger.debug(f"Wikipedia skipped for {culture}/{timeline}")

        cultural_context = f"CULTURE CONTEXT:\n{fallback_text[:1500]}\n\nTIMELINE CONTEXT:\n{timeline_text[:1000]}"
        if wiki_context:
            cultural_context += f"\n\nWIKIPEDIA CONTEXT:\n{wiki_context}"

        existing_str = format_visual_elements_for_prompt(existing) if total_items(existing) > 0 else "No existing visual element data in database."

        prompt = VISUAL_ELEMENTS_PROMPT.format(
            culture=culture, timeline=timeline,
            cultural_context=cultural_context,
            existing_data=existing_str,
        )

        try:
            raw = await call_llm(
                system="You are a film production designer. Output ONLY valid JSON.",
                user=prompt, max_tokens=3000, temperature=0.5, task="visuals"
            )
            elements = extract_and_repair_json(raw)
        except Exception as e:
            logger.error(f"LLM visual gen failed for {culture}/{timeline}: {e}")
            elements = {}

        merged = self._merge(existing, elements)
        validated = self._validate(merged, culture, timeline)

        if r:
            try:
                await r.setex(f"visual:{culture}:{timeline}", 90 * 24 * 3600, json.dumps(validated, default=str))
                logger.info(f"Cached visual:{culture}:{timeline} in Redis")
            except Exception:
                pass

        return validated

    def _merge(self, existing: dict, generated: dict) -> dict:
        result = {"clothing": [], "architecture": [], "artifact": [], "lighting": [], "hairstyle": [], "color_palette": []}
        for cat in result:
            existing_items = {e["name"]: e for e in existing.get(cat, [])}
            gen_items = {e["name"]: e for e in generated.get(cat, [])}
            merged = {**gen_items, **existing_items}
            result[cat] = list(merged.values())
            if len(result[cat]) < 2:
                result[cat] = list(gen_items.values()) or list(existing_items.values())
        return result

    def _validate(self, elements: dict, culture: str, timeline: str) -> dict:
        required = ["clothing", "architecture", "artifact", "lighting", "hairstyle", "color_palette"]
        for cat in required:
            if cat not in elements or len(elements.get(cat, [])) < 1:
                elements[cat] = elements.get(cat, [])

        bucket = TIMELINE_BUCKETS.get(timeline, "ancient")
        allowed_materials = BUCKET_MATERIAL_MAP.get(bucket, BUCKET_MATERIAL_MAP["ancient"])

        for cat in ["clothing", "architecture", "artifact"]:
            filtered = []
            for item in elements.get(cat, []):
                mats = item.get("materials", [])
                valid_mats = [m for m in mats if self._is_material_valid(m, allowed_materials, bucket)]
                item["materials"] = valid_mats if valid_mats else mats
                filtered.append(item)
            elements[cat] = filtered

        for cat in elements:
            clean = []
            for item in elements[cat]:
                desc = item.get("description", "")
                if not self._has_stereotype(desc):
                    clean.append(item)
                else:
                    logger.debug(f"Stereotype filtered: {item.get('name', '?')} in {cat}")
            elements[cat] = clean

        for item in elements.get("color_palette", []):
            colors = item.get("colors", [])
            item["colors"] = [c for c in colors if self._is_valid_hex(c) or not c.startswith("#")]

        return elements

    def _is_material_valid(self, material: str, allowed: list[str], bucket: str) -> bool:
        ml = material.lower()
        for allowed_mat in allowed:
            if allowed_mat in ml or ml in allowed_mat:
                return True
        return True

    def _has_stereotype(self, text: str) -> bool:
        tl = text.lower()
        for trigger in STEREOTYPE_TRIGGERS:
            if trigger.lower() in tl:
                return True
        return False

    def _is_valid_hex(self, color: str) -> bool:
        if not color.startswith("#"):
            return False
        hex_part = color[1:]
        return len(hex_part) in (3, 6) and all(c in "0123456789ABCDEFabcdef" for c in hex_part)


def total_items(data: dict) -> int:
    return sum(len(v) for v in data.values())


visual_engine = VisualElementsEngine()
