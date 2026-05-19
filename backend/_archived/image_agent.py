"""
Chronicles Story Engine - Image Generation Agent
=================================================
Generates multiple consistent images for stories:
- 1 setting/scene image (1024x576, 16:9)
- Up to 3 character portraits (576x1024, 9:16)

Uses deterministic seeding for consistency:
- Same story_hash → same seeds → same images every time

Design Rationale:
- Analyzes BOTH setting field AND story text for richer context
- Extracts visual cues from character descriptions using role keywords
- Deterministic seeds ensure reproducibility (same story = same images)
- Separate aspect ratios: landscape for settings, portrait for characters
"""

import asyncio
import hashlib
import json
import logging
import re
from typing import List, Dict, Optional, Tuple
from urllib.parse import quote

import httpx

from config import CONFIG
from utils import extract_and_repair_json, get_db_fallback, get_visual_elements, format_visual_elements_for_prompt
from utils.llm_client import call_llm

from logger_config import image_logger as logger


VISUAL_DESCRIPTION_PROMPT = """
You are a visual description expert for AI image generation. Analyze this story and extract EXACT VISUAL DETAILS.

SETTING: {setting}
CHARACTERS: {characters}
CULTURE: {culture}
TIMELINE: {timeline}
THEME: {theme}

HISTORICAL & VISUAL CONTEXT:
{visual_context}

STORY:
{narrative}

## YOUR TASK

Generate a JSON object with vivid, camera-ready visual descriptions.

**IMPORTANT:** Use your knowledge of {culture} during {timeline} to make descriptions culturally accurate. Support variation - each character should have unique visual elements (different clothing, props, lighting, expressions).

### 1. "setting_visual" (100-150 words)

Describe the MAIN SCENE/LOCATION with ALL of these elements:

**Architecture & Materials:**
- Building style specific to {culture} (e.g., "Viking longhouse with curved timber beams")
- Exact materials (limestone, thatched roof, mud-brick, carved wood)
- Condition (crumbling, pristine, battle-damaged, weathered)

**Lighting & Time:**
- Time of day (dawn, midday, dusk, night)
- Light source (firelight, sunlight, torchlight, moonlight)
- Light quality (warm, cool, dramatic shadows, soft diffusion)
- Direction (from left, backlighting, overhead)

**Color Palette:**
- 3-5 specific colors (ochre yellow, woad blue, iron-gray, blood-red)
- Dominant color and accent colors

**Atmosphere & Weather:**
- Sky condition (clear, overcast, stormy, starry)
- Atmospheric effects (smoke haze, dust, mist, steam)
- Weather (rain, wind, snow, calm)

**Depth & Composition:**
- Foreground objects (scattered weapons, pottery, footprints)
- Background elements (distant mountains, other buildings, forest)
- Middle ground focus (the main action area)

**Cultural Markers:**
- 2-3 specific items that scream "{culture} {timeline}" (e.g., "Thor's hammer pendant", "knotted quipu records")

Make it historically accurate. Describe what a camera would capture.

### 2. "characters" Array (100-150 words EACH)

For EACH character, create a unique entry with variation:
- "name": Exact character name (must match input)
- "visual": Extremely detailed appearance description

**Include ALL of these in this EXACT ORDER:**

1. **Demographics:** Age range, ethnicity matching {culture}
2. **Face:** Eye color/shape/expression, nose shape, jawline, skin texture, facial hair
3. **Emotional State:** What emotion they feel RIGHT NOW in this story scene (fear, determination, grief, deception)
4. **Unique Features:** Scars, birthmarks, wrinkles, missing limbs, tattoos—specific to their story role
5. **Hair:** Style, length, color, texture, how worn (braided, loose, shaved, covered)
6. **Body:** Height, build, posture, notable physical traits from their story actions
7. **Clothing - Fabric:** Exact material (rough-spun wool, linen, silk, leather, chainmail)
8. **Clothing - Color:** Natural dye colors (woad blue, madder red, ochre yellow, undyed brown)
9. **Clothing - Style:** Culture-specific garments (Viking tunic, Roman toga, Chola drape)
10. **Clothing - Condition:** New, worn, battle-damaged, patched, ceremonial
11. **Accessories:** Jewelry, weapons, tools, bags, religious symbols—items mentioned or implied in story
12. **Pose & Gesture:** What their body is doing (gripping sword, slumped shoulders, avoiding eye contact)
13. **Mood Expression:** How their face shows the emotion from the story

**CRITICAL:** Base ALL details on what happens IN THE STORY. If a character is deceptive, show it in their expression. If they're a warrior, show battle weariness. If they're grieving, show it in their posture. Use your knowledge of {culture} during {timeline} for culturally accurate details.

## RULES

- Output ONLY valid JSON. No markdown, no commentary, no explanations.
- Focus on VISUAL/PHYSICAL details only—what a camera captures.
- Make descriptions SPECIFIC to THIS story, not generic templates.
- Include ALL characters from the input list.
- Be historically accurate to {culture} during {timeline}.
- Use sensory language: colors, textures, lighting, expressions.
- Show emotion through PHYSICAL DETAILS, not abstract states.
- SUPPORT VARIATION: Each character should have unique visual elements (different clothing colors, different props, different lighting, different expressions).

## EXAMPLE OUTPUT

{{
  "setting_visual": "A Viking longhouse interior at dusk, curved oak timber beams arching overhead like a ship's hull, smoke from the central hearth creating amber haze that catches firelight. Rough-hewn wooden tables scarred with knife marks dominate the foreground, scattered with drinking horns and a toppled bronze bowl. Stone walls hung with faded blue wool tapestries depicting sea serpents. Iron lanterns cast warm orange glow on the left, deep shadows on the right. In the background, a carved wooden throne with dragon-head armrests sits empty. The packed earth floor shows recent struggle—overturned stools, scattered grain, a single bloodstain. Outside the narrow window, twilight sky burns crimson and violet.",
  "characters": [
    {{
      "name": "Ragnar Frostskjold",
      "visual": "A Norse man in his mid-40s with weathered olive-brown skin from decades at sea. Deep-set steel-gray eyes under heavy furrowed brows, prominent aquiline nose, square jaw clenched tight. A jagged pink scar runs from his left temple to his cheekbone. Salt-and-pepper hair in thick warrior braids down to his shoulders, full beard with silver streaks. Tall and broad-shouldered, muscular frame still powerful but showing age, thick forearms crossed defensively. Wears a knee-length tunic of undyed wool with leather reinforcements at shoulders, dark blue cloak fastened with a silver raven brooch. Iron sword belt with family crest buckle, leather bracers scarred from battle. His posture is tense, weight forward, hand hovering near sword hilt. Expression shows inner conflict—jaw tight with determination but eyes betraying doubt and sorrow."
    }}
  ]
}}
"""

SETTING_QUALITY = (
    "cinematic wide-angle photograph, anamorphic lens, "
    "golden hour lighting, detailed textures, photorealistic, "
    "atmospheric haze, color grading like a historical epic film, "
    "8K resolution, no text, no watermark, no frame"
)

CHARACTER_QUALITY = (
    "hyperrealistic portrait photograph, 85mm lens, shallow depth of field, "
    "studio lighting with warm rim light, sharp focus on face, "
    "detailed skin texture, photorealistic, 8K resolution, "
    "no text, no watermark, no cartoon, no anime, no deformed features"
)


class ImageGenerationAgent:
    """
    Multi-image generation agent with consistency tracking.

    Generates:
    - 1 setting image (key location from story + setting field)
    - 1-3 character portraits (main characters with visual cues)

    All images use deterministic seeds based on story_hash,
    ensuring the same story always produces the same images.
    """

    BASE_URL = "https://gen.pollinations.ai/image"

    SETTING_WIDTH = 1344
    SETTING_HEIGHT = 768
    CHARACTER_WIDTH = 768
    CHARACTER_HEIGHT = 1344

    MODEL = "flux"
    NOLOGO = True
    SAFE = True

    ROLE_KEYWORDS = {
        "merchant": "trading robes, coin purse, jewelry, wealthy attire",
        "warrior": "armor, weapon, battle scars, muscular build",
        "priest": "ceremonial robes, religious symbols, sacred items",
        "scribe": "writing tools, scrolls, ink stains, scholarly appearance",
        "king": "crown, royal robes, scepter, regal bearing",
        "queen": "diadem, elegant gown, jewelry, noble posture",
        "blacksmith": "leather apron, muscular build, soot stains, hammer",
        "dancer": "flowing garments, jewelry, graceful posture, ornate costume",
        "skald": "poet robes, lyre or harp, wise expression, elderly",
        "assessor": "formal robes, scroll case, authoritative bearing",
        "chief": "tribal regalia, ceremonial weapons, leadership symbols",
        "elder": "wrinkled face, wise eyes, ceremonial garments, staff",
        "hunter": "leather armor, bow, quiver, weathered skin",
        "fisher": "simple tunic, fishing net, weather-beaten face",
        "soldier": "chainmail, sword, shield, battle-worn armor",
        "noble": "fine silk garments, embroidered details, jewelry",
        "peasant": "simple wool tunic, worn tools, calloused hands",
        "monk": "simple robes, prayer beads, shaved head or hood",
        "wizard": "flowing robes, staff, mystical symbols, aged",
        "thief": "dark hooded cloak, daggers, shadowy appearance",
    }

    def __init__(self):
        logger.info("Image generation agent initialized")

    async def _generate_llm_visuals(
        self, story_data: dict, timeout: float = 45.0
    ) -> Optional[dict]:
        setting = story_data.get("setting", "")
        characters = story_data.get("characters", [])
        narrative = story_data.get("story", "")
        metadata = story_data.get("metadata", {})
        culture = metadata.get("culture_display", "unknown")
        timeline = metadata.get("timeline_display", "unknown")
        theme = metadata.get("theme_display", "unknown")

        if not narrative:
            logger.debug("No narrative for LLM visual gen, skipping")
            return None

        char_list = "\n".join(
            f"- {c}" for c in characters[:5]
        ) if characters else "- No named characters"

        culture_slug = metadata.get("culture", "")
        timeline_slug = metadata.get("timeline", "")
        theme_slug = metadata.get("theme", "")
        visual_context_text, visual_data_dict = self.get_visual_context(culture_slug, timeline_slug, theme_slug)
        visual_context = visual_context_text

        prompt = VISUAL_DESCRIPTION_PROMPT.format(
            setting=setting[:500],
            characters=char_list,
            culture=culture,
            timeline=timeline,
            theme=theme,
            visual_context=visual_context,
            narrative=narrative[:4000],
        )

        try:
            system = "You are a visual description expert for AI image generation. Output ONLY valid JSON."
            raw = await call_llm(
                system=system,
                user=prompt,
                max_tokens=2500,
                temperature=0.6,
                task="visuals",
            )
            visuals = extract_and_repair_json(raw)

            if "setting_visual" not in visuals:
                logger.warning("LLM visuals missing 'setting_visual' key")
                return None
            if "characters" not in visuals or not isinstance(visuals["characters"], list):
                logger.warning("LLM visuals missing valid 'characters' list")
                return None

            logger.info(
                f"LLM visual descriptions generated: setting + {len(visuals['characters'])} characters"
            )
            return visuals

        except asyncio.TimeoutError:
            logger.warning(f"LLM visual gen timed out after {timeout}s, using keyword fallback")
        except json.JSONDecodeError as e:
            logger.warning(f"LLM visual gen returned invalid JSON: {e}")
        except RuntimeError as e:
            logger.warning(f"LLM visual gen failed: {e}, using keyword fallback")

        return None

    def _apply_llm_visuals(
        self,
        llm_visuals: dict,
        story_data: dict,
    ) -> Tuple[str, str, List[Dict]]:
        metadata = story_data.get("metadata", {})
        culture = metadata.get("culture_display", "")
        timeline = metadata.get("timeline_display", "")
        theme = metadata.get("theme_display", "")

        setting_visual = llm_visuals.get("setting_visual", "")
        setting_prompt = (
            f"{setting_visual}, {culture} {timeline} era, "
            f"{theme} mood, {SETTING_QUALITY}"
        )
        scene_desc = setting_visual[:100] if setting_visual else "Story setting"

        llm_chars = {c["name"]: c["visual"] for c in llm_visuals.get("characters", [])}
        characters = story_data.get("characters", [])
        character_data = []

        for char in characters[:5]:
            if isinstance(char, str) and ":" in char:
                name = char.split(":", 1)[0].strip()
                description = char.split(":", 1)[1].strip()
            else:
                name = str(char)
                description = ""

            llm_visual = llm_chars.get(name, "")
            if llm_visual:
                setting_context = setting_visual[:80] if setting_visual else ""
                visual_cues = (
                    f"{llm_visual}, set in {setting_context}, "
                    f"{culture} {timeline} era, "
                    f"{CHARACTER_QUALITY}"
                )
            else:
                visual_cues = self._build_character_visual_cues(
                    name, description, culture, timeline
                )

            character_data.append({
                "name": name,
                "description": description,
                "visual_cues": visual_cues,
            })

        return setting_prompt, scene_desc, character_data

    def compute_seed(self, base_hash: str, suffix: str = "") -> int:
        combined = f"{base_hash}{suffix}"
        seed = abs(hash(combined)) % 9999
        logger.debug(f"Computed seed {seed} for {base_hash[:8]}...{suffix}")
        return seed

    def extract_setting_scene(self, story_data: dict) -> Tuple[str, str]:
        setting = story_data.get("setting", "")
        story = story_data.get("story", "")

        if not setting:
            return ("Ancient city marketplace", "bustling, atmospheric")

        scene = setting.split(".")[0].strip()
        if len(scene) < 20:
            scene = setting[:150].rstrip(",.!?")

        atmosphere = self._extract_atmosphere(story)
        return (scene, atmosphere)

    def _extract_atmosphere(self, story: str) -> str:
        if not story:
            return "atmospheric, cinematic"

        story_lower = story.lower()
        atmosphere_map = {
            "dark": "dark shadows, dramatic lighting",
            "bright": "bright sunlight, golden hour",
            "sun": "warm sunlight, golden rays",
            "moon": "moonlight, silver glow, night",
            "fire": "flickering firelight, warm glow",
            "torch": "torchlight, dancing shadows",
            "mist": "misty, ethereal fog",
            "fog": "foggy, mysterious atmosphere",
            "storm": "stormy clouds, dramatic sky",
            "rain": "rain-slicked, overcast",
            "snow": "snow-covered, winter atmosphere",
            "dawn": "dawn light, soft morning glow",
            "dusk": "dusk, twilight, fading light",
            "night": "night sky, starlight",
            "ancient": "ancient stones, weathered textures",
            "ruined": "ruins, crumbling architecture",
            "sacred": "sacred atmosphere, reverent lighting",
            "royal": "opulent, regal splendor",
            "humble": "humble surroundings, simple textures",
        }

        found_elements = []
        for keyword, description in atmosphere_map.items():
            if keyword in story_lower and len(found_elements) < 3:
                found_elements.append(description)

        if found_elements:
            return ", ".join(found_elements)

        return "atmospheric, cinematic"

    def extract_characters(self, story_data: dict) -> List[Dict]:
        characters = story_data.get("characters", [])
        metadata = story_data.get("metadata", {})
        culture = metadata.get("culture_display", "")
        timeline = metadata.get("timeline_display", "")

        character_data = []
        for char in characters[:5]:
            if isinstance(char, str) and ":" in char:
                parts = char.split(":", 1)
                name = parts[0].strip()
                description = parts[1].strip() if len(parts) > 1 else ""
            else:
                name = str(char)
                description = ""

            visual_cues = self._build_character_visual_cues(
                name, description, culture, timeline
            )

            character_data.append({
                "name": name,
                "description": description,
                "visual_cues": visual_cues,
            })

        return character_data

    def _build_character_visual_cues(
        self,
        name: str,
        description: str,
        culture: str,
        timeline: str
    ) -> str:
        description_lower = description.lower()

        role = ""
        for keyword, visual in self.ROLE_KEYWORDS.items():
            if keyword in description_lower:
                role = visual
                break

        if not role:
            role = "period-appropriate clothing, detailed attire"

        visual_data = get_visual_elements(culture, timeline)
        db_clothing = ""
        db_hairstyle = ""

        if visual_data.get("clothing"):
            clothing_descs = []
            for c in visual_data["clothing"][:2]:
                mats = ", ".join(c["materials"][:2]) if c["materials"] else ""
                colors = ", ".join(c["colors"][:2]) if c["colors"] else ""
                clothing_descs.append(f'{c["description"]} ({mats}, {colors})')
            db_clothing = ", ".join(clothing_descs)

        if visual_data.get("hairstyle"):
            h = visual_data["hairstyle"][0]
            db_hairstyle = h["description"]

        parts = [f"{name}", f"{culture} {timeline} era"]
        if db_clothing:
            parts.append(db_clothing)
        else:
            parts.append(role)
        if db_hairstyle:
            parts.append(db_hairstyle)
        parts.append(CHARACTER_QUALITY)

        visual = ", ".join(parts)
        return visual

    def get_visual_context(self, culture: str, timeline: str, theme: str = "") -> Tuple[str, dict]:
        visual_data = get_visual_elements(culture, timeline)
        total_items = sum(len(v) for v in visual_data.values())

        context_parts = []

        if total_items > 0:
            context_parts.append(format_visual_elements_for_prompt(visual_data))
            logger.info(f"Visual context: {total_items} DB elements for {culture}/{timeline}")

        culture_fallback = get_db_fallback("culture", culture)
        timeline_fallback = get_db_fallback("timeline", timeline)
        theme_fallback = get_db_fallback("theme", theme) if theme else ""

        if culture_fallback:
            context_parts.append(f"CULTURAL CONTEXT:\n{culture_fallback[:800]}")
        if timeline_fallback:
            context_parts.append(f"TIMELINE CONTEXT:\n{timeline_fallback[:800]}")
        if theme_fallback:
            context_parts.append(f"THEME CRAFT NOTES:\n{theme_fallback[:500]}")

        if not context_parts:
            return "No DB context available for this combination.", visual_data

        formatted = "\n\n".join(context_parts)
        return formatted, visual_data

    def build_setting_prompt(self, scene: str, atmosphere: str, story_data: dict) -> str:
        metadata = story_data.get("metadata", {})
        culture = metadata.get("culture", "")
        timeline = metadata.get("timeline", "")
        theme = metadata.get("theme_display", "")
        culture_display = metadata.get("culture_display", culture.replace('_', ' ').title())
        timeline_display = metadata.get("timeline_display", timeline.replace('_', ' ').title())

        visual_data = get_visual_elements(culture, timeline)

        prompt_parts = [scene]

        if visual_data.get("architecture"):
            arch_descs = [a["description"] for a in visual_data["architecture"][:3]]
            arch_mats = []
            for a in visual_data["architecture"][:3]:
                arch_mats.extend(a.get("materials", []))
            prompt_parts.append(", ".join(arch_descs))
            if arch_mats:
                prompt_parts.append(f"materials: {', '.join(set(arch_mats))}")

        if visual_data.get("lighting"):
            light_descs = [l["description"] for l in visual_data["lighting"][:2]]
            prompt_parts.append(", ".join(light_descs))

        if visual_data.get("artifact"):
            artifact_descs = [a["description"] for a in visual_data["artifact"][:3]]
            prompt_parts.append(", ".join(artifact_descs))

        if visual_data.get("color_palette"):
            all_hex = []
            for p in visual_data["color_palette"]:
                all_hex.extend(p.get("colors", [])[:4])
            if all_hex:
                prompt_parts.append(f"color palette: {', '.join(set(all_hex))}")

        if not any(visual_data.get(k) for k in ["architecture", "lighting", "artifact", "color_palette"]):
            prompt_parts.append(f"{culture_display} {timeline_display} era")
            prompt_parts.append("historically accurate architecture and clothing")

        prompt_parts.append(atmosphere)
        prompt_parts.append(f"{theme} mood")
        prompt_parts.append(SETTING_QUALITY)

        prompt = ", ".join([p for p in prompt_parts if p])

        total_elements = sum(len(v) for v in visual_data.values())
        logger.info(f"Setting prompt built with {total_elements} DB visual elements")

        return prompt

    def build_character_prompt(self, char_data: dict, story_data: dict) -> str:
        metadata = story_data.get("metadata", {})
        theme = metadata.get("theme_display", "")

        prompt = (
            f"{char_data['visual_cues']}, "
            f"{theme} expression, portrait orientation, "
            f"dramatic lighting, intricate details, character concept art"
        )

        return prompt

    def _build_image_url(
        self,
        prompt: str,
        seed: int,
        orientation: str = "landscape"
    ) -> str:
        clean_prompt = self._sanitize_prompt(prompt)
        encoded_prompt = quote(clean_prompt, safe='')

        if orientation == "portrait":
            width = self.CHARACTER_WIDTH
            height = self.CHARACTER_HEIGHT
        else:
            width = self.SETTING_WIDTH
            height = self.SETTING_HEIGHT

        api_key = CONFIG.POLLINATIONS_API_KEY
        url = (
            f"{self.BASE_URL}/{encoded_prompt}"
            f"?width={width}&height={height}"
            f"&model={self.MODEL}"
            f"&nologo={str(self.NOLOGO).lower()}"
            f"&safe={str(self.SAFE).lower()}"
            f"&seed={seed}"
        )
        if api_key:
            url += f"&key={api_key}"

        logger.debug(f"Built image URL ({orientation}): {url[:80]}...")
        return url

    @staticmethod
    def _sanitize_prompt(prompt: str) -> str:
        prompt = prompt.replace("**", "").replace("__", "")
        prompt = prompt.replace("_", " ")
        prompt = prompt.replace(";", ",")
        prompt = prompt.replace('"', '').replace("'", "")
        prompt = re.sub(r'\s+', ' ', prompt).strip()
        if len(prompt) > 800:
            prompt = prompt[:800].rsplit(' ', 1)[0]
        return prompt

    async def generate_all_images(
        self,
        story_data: dict,
        story_hash: str,
        cached_visuals: Optional[dict] = None,
    ) -> Dict:
        results = {
            "setting": None,
            "characters": [],
            "seeds": {},
        }

        if cached_visuals:
            llm_visuals = cached_visuals
            source = "cached"
            logger.info("Using cached LLM visuals (instant)")
        else:
            llm_visuals = await self._generate_llm_visuals(story_data)
            source = "llm" if llm_visuals else "keyword"

        if llm_visuals:
            setting_prompt, scene_desc, character_data = self._apply_llm_visuals(
                llm_visuals, story_data
            )
            atmosphere = "llm-generated"
        else:
            scene_desc, atmosphere = self.extract_setting_scene(story_data)
            setting_prompt = self.build_setting_prompt(scene_desc, atmosphere, story_data)
            character_data = self.extract_characters(story_data)

        setting_seed = self.compute_seed(story_hash, "_setting")
        setting_url = self._build_image_url(setting_prompt, setting_seed, "landscape")

        results["setting"] = {
            "url": setting_url,
            "prompt": setting_prompt,
            "scene": scene_desc,
            "atmosphere": atmosphere,
            "seed": setting_seed,
            "source": source,
        }
        results["seeds"]["setting"] = setting_seed

        for char in character_data:
            char_prompt = (
                f"{char['visual_cues']}, "
                f"{story_data.get('metadata', {}).get('theme_display', '')} expression, "
                f"portrait orientation"
            ) if source in ("llm", "cached") else self.build_character_prompt(char, story_data)

            char_seed = self.compute_seed(
                story_hash, f"_char_{char['name'].lower().replace(' ', '_')}"
            )
            char_url = self._build_image_url(char_prompt, char_seed, "portrait")

            results["characters"].append({
                "url": char_url,
                "prompt": char_prompt,
                "character": char["name"],
                "seed": char_seed,
                "source": source,
            })
            results["seeds"][f"char_{char['name']}"] = char_seed

        logger.info(
            f"Constructed image URLs ({source}): 1 setting + {len(results['characters'])} characters "
            f"for story {story_hash[:8]}..."
        )

        if llm_visuals and source != "cached":
            results["_visuals"] = llm_visuals

        return results


image_agent = ImageGenerationAgent()
