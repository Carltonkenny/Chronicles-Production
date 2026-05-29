from agents.base_agent import BaseAgent
from schemas import WorkOrder, WorkResult
from utils.llm_client import call_llm
from logger_config import setup_logger
from utils import get_visual_elements

logger = setup_logger("VisualBibleArchitect")

VBA_SYSTEM = """You are a Visual Bible Architect — a master film-maker combining three traditions:

DIRECTOR (Villeneuve, Miyazaki, Iñárritu): You define the creative vision. You think in LIGHT, COMPOSITION, CAMERA LANGUAGE. You know focal lengths (24mm wide, 35mm environmental, 50mm human eye, 85mm portrait, 135mm compressed), shot types, and movement vocabulary. Rule: no two consecutive shots share the same focal length.

PRODUCTION DESIGNER (Ferretti, Martin, Caballero): You build the physical world. You think in MATERIALS — exact, specific: "limestone" not "stone", "oak" not "wood", "wrought iron" not "metal". You think in COLOR TEMPERATURE: warm 2700K, neutral 4000K, cool 6500K. You think in SHADOW QUALITY: hard, soft, deep, diffused.

ART DIRECTOR (props, symbols, motifs): You make every frame feel authentic through specific, intentional objects. You know that a Roman gladius is not a Viking sword, that a Mauryan silk dhoti is not a Japanese kimono. You find the cultural symbols that ONLY {culture} {timeline} would have.

Output ONLY valid JSON matching the exact schema below. No markdown, no explanations."""

VBA_PROMPT = """## STORY CONTEXT
Title: {title}
Culture: {culture}
Timeline: {timeline}
Theme: {theme}
Story: {story_snippet}

## CHARACTERS
{characters_text}

## SCENES
{scenes_text}

## VISUAL ELEMENTS DATABASE (primary source for cultural accuracy)
{visual_elements_text}

## YOUR TASK — Complete Visual Bible

### CULTURAL AUTHENTICITY CHECKLIST (verify before outputting)
- [ ] Every material exists in {culture} during {timeline}
- [ ] No anachronisms (test: would a {timeline} person recognize every object listed?)
- [ ] Signature items are culturally authentic: Viking = axe/shield/arm-ring, Roman = gladius/stylus/toga/fibula, Japanese = katana/tessen/sake-cup, Mauryan = dhoti/kundala/turban
- [ ] All hex codes are valid 6-character: e.g. #1E3A5F not "navy blue"
- [ ] Lighting decisions include color temperature in Kelvin
- [ ] Camera descriptions use real focal lengths and movement terminology

### OUTPUT JSON SCHEMA (MUST follow this exact structure)

{{
  "film_tone": "1-sentence visual atmosphere. Example: 'Dark, brooding, fire-lit with moments of cold dawn introspection'",
  "pacing": "Tempo arc. Example: 'Slow atmospheric discovery → building tension → frantic climax → quiet earned resolution'",
  "color_palette": {{"primary": ["#HEX", "#HEX", "#HEX"], "accent": ["#HEX", "#HEX"]}},
  "lighting_style": "Overall lighting approach. Example: 'Low-key with fire as primary source, deep warm shadows, cool blue ambient for exteriors'",

  "character_bibles": [
    {{
      "name": "Exact character name",
      "role": "Their function in the story",
      "appearance": "Detailed physical description: face shape, build, skin tone, hair, eyes, distinguishing marks/scars/tattoos",
      "costume": "Culture-specific garments with EXACT materials and colors",
      "signature_items": ["1-2 visually distinctive items they always carry or wear"],
      "emotional_range": "Their emotional journey through the film",
      "voice_traits": "How they sound: pitch, tempo, accent, emotional quality (e.g. 'gravelly baritone, speaks slowly, carries weight in every word')"
    }}
  ],

  "location_descriptions": [
    {{
      "name": "Location identifier",
      "description": "Rich visual description with architecture, atmosphere, condition (new/weathered/ruined/sacred)",
      "materials": ["EXACT materials: limestone, oak, wrought iron, terracotta — never generic 'stone' or 'wood'"],
      "lighting": "Light source + color temperature in Kelvin (2700K warm through 6500K cool) + shadow quality",
      "time_of_day": "dawn, morning, midday, afternoon, dusk, night",
      "atmosphere": "Weather, particulates (dust/smoke/mist/pollen/steam), sensory qualities"
    }}
  ],

  "material_inventory": ["COMPREHENSIVE: every exact material visible in the film — architecture, props, clothing, environment"],

  "scene_props": {{
    "1": [
      {{"prop": "Specific prop name", "character": "Who interacts with it", "purpose": "Why it matters to the story"}}
    ]
  }},

  "cultural_symbols": [
    {{
      "symbol": "Culturally specific symbol (NOT generic — no yin-yang for Viking stories)",
      "meaning": "What it represents in {culture}",
      "theme_connection": "How it connects to the theme: {theme}",
      "appears_in": "Which scenes/characters carry this symbol"
    }}
  ],

  "signature_item_placement": [
    {{
      "item": "Signature item name",
      "character": "Owner",
      "first_seen": "When it first appears (opening scene)",
      "key_moments": ["Climax moment", "Turning point"],
      "condition_arc": "How its physical state changes: pristine → worn → damaged → lost → recovered. Example: 'Worn but well-maintained → glowing from forge heat → cracks on final strike'"
    }}
  ],

  "motif_arc": "How one visual element transforms through the story. Example: 'Fire: warm hearth safety → raging forge obsession → consuming blaze at climax → dying embers acceptance'",

  "shot_variation_matrix": {{
    "scene_1": [
      {{"shot_id": "scene_1_shot_1", "shot_type": "wide establishing | medium | close-up | extreme close-up | over-shoulder | POV", "focal_length": "24mm | 35mm | 50mm | 85mm | 135mm", "movement": "static | slow push-in | dolly left | dolly right | crane up | crane down | handheld | dutch angle", "description": "What the camera captures in this shot"}}
    ]
  }},

  "emotion_camera_map": [
    {{"emotion": "wonder | fear | obsession | grief | determination | hope | remorse | rage | love | tension", "camera_style": "DOF + angle + framing + movement. Example: 'Wonder: slow push-in, shallow DOF, 35mm, eye-level. Obsession: tight dutch angle, deep focus, 85mm, handheld.'"}}
  ],

  "camera_language": "Overall camera philosophy for the entire film. How the camera tells THIS specific story."
}}

### SECTION A: Director's Vision
Define the film's visual soul — tone, pacing, color, lighting. One powerful sentence each.

### SECTION B: Character Bibles
Each character gets a complete visual identity. The signature items are the PRIMARY mechanism for character consistency across all video clips — choose visually distinctive, era-authentic items.

### SECTION C: Location Descriptions
Every location must be filmable. After writing each location, verify: can a set designer build this from the materials listed?

### SECTION D: Material Inventory
Every material that would appear on screen. Be exhaustive. The Production Designer's voice demands specificity.

### SECTION E: Props & Cultural Symbols
This is where the Art Director's eye matters most. Every prop must have story purpose (ask: why is THIS object here?). Every symbol must be authentic to {culture} (ask: would a {culture} person recognize and respect this representation?). The motif arc is a gift to the editor — it gives them a visual thread to weave.

### SECTION F: Shot & Camera
The Director's technical vocabulary in action. Shot variation: no two consecutive shots share focal length. Camera language matches emotional arc — wonder gets wide slow push-ins, obsession gets tight dutch angles, grief gets static distant framing.

## OUTPUT
Valid JSON matching the exact schema above. Every field present. Every material EXACT. Every hex code valid. Every cultural reference authentic to {culture} {timeline}."""



class VisualBibleArchitect(BaseAgent):
    agent_type = "visual_bible_architect"

    async def _execute_internal(self, work_order: WorkOrder) -> WorkResult:
        data = work_order.input_data
        culture = data.get("culture", "")
        timeline = data.get("timeline", "")
        theme = data.get("theme", "")
        story = data.get("story", "")
        characters = data.get("characters", [])
        scenes = data.get("scenes", [])

        visual_elements = get_visual_elements(culture, timeline)

        import json as _json

        chars_text = "\n".join(
            c if isinstance(c, str) else f"{c.get('name', '?')}: {c.get('description', '')}"
            for c in characters
        )

        scenes_text = ""
        for s in scenes[:12]:
            if isinstance(s, dict):
                scenes_text += f"Scene {s.get('id', '?')}: {s.get('summary', '')} [{s.get('location', '')}] Beat: {s.get('emotional_beat', 'neutral')}\n"

        ve_text = _json.dumps({
            cat: items[:5] for cat, items in visual_elements.items()
        }, indent=2, default=str)

        prompt = VBA_PROMPT.format(
            title=data.get("title", "Untitled"),
            culture=culture,
            timeline=timeline,
            theme=theme,
            story_snippet=story[:300] if story else "",
            characters_text=chars_text or "None",
            scenes_text=scenes_text or "None",
            visual_elements_text=ve_text or "None available",
        )

        try:
            llm_result = await call_llm(
                system=VBA_SYSTEM,
                user=prompt,
                temperature=0.5,
                max_tokens=6000,
                task="visuals",
            )
            text = llm_result.strip() if isinstance(llm_result, str) else "{}"
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            visual_bible = _json.loads(text)
        except (RuntimeError, _json.JSONDecodeError) as e:
            logger.error(f"VisualBibleArchitect failed: {e}")
            visual_bible = {
                "film_tone": f"A {theme} story set in {culture} {timeline} era",
                "color_palette": {"primary": ["#8B4513", "#DAA520"], "accent": ["#2F4F4F", "#CD853F"]},
                "lighting_style": "Natural period lighting",
                "character_bibles": [{"name": c if isinstance(c, str) else c.get("name", "Unknown"), "appearance": "", "costume": "", "signature_items": [], "emotional_range": "neutral"} for c in characters],
                "location_descriptions": [],
                "material_inventory": [],
                "scene_props": {},
                "cultural_symbols": [],
                "signature_item_placement": {},
                "motif_arc": "",
                "camera_language": "Period-appropriate cinematography",
            }

        themes_str = f"{theme} film set in {culture} {timeline} era"
        if "film_tone" not in visual_bible:
            visual_bible["film_tone"] = themes_str

        char_count = len(visual_bible.get("character_bibles", []))
        loc_count = len(visual_bible.get("location_descriptions", []))
        self.tokens_used = 6000
        logger.info(
            f"[{self.agent_type}] Visual Bible: {char_count} chars, "
            f"{loc_count} locations, {len(visual_bible.get('material_inventory', []))} materials"
        )

        return WorkResult(
            success=True,
            output_data=visual_bible,
            wall_time_ms=self.wall_time_ms,
            tokens_used=self.tokens_used,
        )
