from agents.base_agent import BaseAgent
from schemas import WorkOrder, WorkResult
from utils.llm_client import call_llm
from config import CONFIG
from logger_config import setup_logger

logger = setup_logger("WriterSceneAgent")

WRITER_SCENE_SYSTEM = """You are a master storyteller and script supervisor for a short film studio.
Given a story blueprint, write a complete narrative (600-900 words) AND break it into 6-12 scenes.

Output ONLY valid JSON. No markdown, no explanations."""

WRITER_SCENE_PROMPT = """## STORY BLUEPRINT
Title: {title}
Setting: {setting}
Characters: {characters}
Plot Outline: {plot_outline}
Scenes Outline: {scenes_outline}

## WORLD CONTEXT
Culture: {culture}
Timeline: {timeline}
Theme: {theme}
Seed Idea: {seed_idea}
Wikipedia Context: {wiki_context}

## YOUR TASK

### PART 1: Narrative (600-900 words)
Write a complete short film narrative. Include vivid descriptions, character moments, and emotional arcs.
The story should be self-contained with a clear beginning, middle, and end.

### PART 2: Scene Breakdown
Break your narrative into 6-12 discrete scenes. Each scene:
- Has a unique numeric ID
- Summary (1-2 sentences)
- Location description
- Characters present (list)
- Emotional beat (wonder, tension, grief, joy, fear, revelation, etc.)
- Narration text (2-3 sentences for voiceover, leave empty if not needed)
- Duration estimate in seconds (5-15s)

### PART 3: Character Dialogues
For important character interactions, write 1-3 lines of dialogue per speaking character per scene.
Only write dialogue for emotionally significant moments. Format as:
"{{character_name}} ({{tone}}): '{{dialogue_line}}'"

## OUTPUT JSON
{{
  "title": "Film title",
  "setting": "Time and place",
  "characters": ["Name: description", ...],
  "story": "Complete narrative text (600-900 words)...",
  "scenes": [
    {{
      "id": 1,
      "summary": "Scene summary",
      "location": "Location name",
      "characters": ["Character A", "Character B"],
      "emotional_beat": "wonder",
      "narration_text": "Optional narration...",
      "duration_estimate": 10
    }}
  ],
  "dialogues": {{
    "1": ["Hakon (gravelly): 'The forge burns cold tonight.'"],
    "2": []
  }}
}}

## RULES
- Story MUST be 600-900 words
- 6-12 scenes
- Each scene has a distinct emotional beat
- Characters remain consistent across scenes
- Dialogue fits the culture/timeline voice
- No modern slang in historical settings

## SELF-AUDIT CHECKLIST (verify before outputting)
- [ ] Story word count: between 600-900 words
- [ ] Scene count: between 6-12 scenes
- [ ] Every character from the blueprint appears in at least ONE scene
- [ ] Emotional beats are distinct — no two consecutive scenes share the same emotional beat
- [ ] Dialogue lines only for emotionally significant moments (silence is better than filler dialogue)
- [ ] Narration text is present for at least the opening scene and climax scene
- [ ] No modern slang or anachronistic language in dialogue (test: would a {culture} {timeline} person use these words?)
- [ ] Characters present in scenes use EXACT names from the character list — no invented characters
"""


class WriterSceneAgent(BaseAgent):
    agent_type = "writer_scene"

    async def _execute_internal(self, work_order: WorkOrder) -> WorkResult:
        data = work_order.input_data
        blueprint = data.get("blueprint", {})
        seed_idea = data.get("seed_idea", "")
        culture = data.get("culture", "")
        timeline = data.get("timeline", "")
        theme = data.get("theme", "")
        wiki_context = data.get("wiki_context", "")

        title = blueprint.get("title", "Untitled")
        setting = blueprint.get("setting", "")
        characters = blueprint.get("characters", [])
        plot_outline = blueprint.get("plot_outline", "")
        scenes_outline = blueprint.get("scenes_outline", "")

        chars_text = "\n".join(
            c if isinstance(c, str) else f"{c.get('name', '?')}: {c.get('description', '')}"
            for c in characters
        )

        prompt = WRITER_SCENE_PROMPT.format(
            title=title,
            setting=setting,
            characters=chars_text or "None",
            plot_outline=plot_outline or "None",
            scenes_outline=scenes_outline or "None",
            culture=culture,
            timeline=timeline,
            theme=theme,
            seed_idea=seed_idea,
            wiki_context=wiki_context or "None",
        )

        import json as _json
        try:
            llm_result = await call_llm(
                system=WRITER_SCENE_SYSTEM,
                user=prompt,
                temperature=CONFIG.WRITER_TEMPERATURE,
                max_tokens=4000,
                task="writer",
            )
            text = llm_result.strip() if isinstance(llm_result, str) else "{}"
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            output = _json.loads(text)
        except (RuntimeError, _json.JSONDecodeError) as e:
            logger.error(f"WriterScene failed: {e}")
            output = {
                "title": title,
                "story": f"{setting}. {plot_outline}",
                "scenes": [{"id": 1, "summary": "Opening scene", "location": setting, "characters": [], "emotional_beat": theme, "narration_text": "", "duration_estimate": 10}],
                "dialogues": {},
            }

        story_word_count = len(output.get("story", "").split())
        scene_count = len(output.get("scenes", []))

        self.tokens_used = 4000
        logger.info(
            f"[{self.agent_type}] Generated {story_word_count} words, "
            f"{scene_count} scenes, {sum(len(v) for v in output.get('dialogues', {}).values())} dialogue lines"
        )

        return WorkResult(
            success=True,
            output_data=output,
            wall_time_ms=self.wall_time_ms,
            tokens_used=self.tokens_used,
        )
