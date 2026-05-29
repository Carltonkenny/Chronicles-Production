from agents.base_agent import BaseAgent
from schemas import WorkOrder, WorkResult
from prompts.sound_designer_prompt import SOUND_DESIGNER_PROMPT, SOUND_DESIGNER_SYSTEM
from utils.llm_client import call_llm
from logger_config import setup_logger

logger = setup_logger("SoundDesignerAgent")


class SoundDesignerAgent(BaseAgent):
    agent_type = "sound_designer"

    async def _execute_internal(self, work_order: WorkOrder) -> WorkResult:
        data = work_order.input_data
        culture = data.get("culture", "")
        timeline = data.get("timeline", "")
        scenes = data.get("scenes", [])
        characters = data.get("characters", [])

        scenes_text = ""
        for s in scenes[:12]:
            if isinstance(s, dict):
                scenes_text += (
                    f"Scene {s.get('id', '?')}: {s.get('summary', '')} "
                    f"[{s.get('location', '')}] "
                    f"Beat: {s.get('emotional_beat', 'neutral')} "
                    f"Chars: {s.get('characters', [])}\n"
                )

        characters_text = ""
        for c in characters:
            if isinstance(c, dict):
                name = c.get("name", "")
                role = c.get("role", "")
                voice_traits = c.get("voice_traits", "")
                characters_text += f"- {name} ({role})"
                if voice_traits:
                    characters_text += f": {voice_traits}"
                characters_text += "\n"

        prompt = SOUND_DESIGNER_PROMPT.format(
            culture=culture,
            timeline=timeline,
            scenes=scenes_text or "No scenes",
            characters=characters_text or "No characters",
        )

        llm_result = await call_llm(
            system=SOUND_DESIGNER_SYSTEM,
            user=prompt,
            temperature=0.4,
            max_tokens=1500,
            task="default",
        )

        self.tokens_used = 0

        import json as _json
        audio_prompts = {}
        try:
            if isinstance(llm_result, str):
                text = llm_result.strip()
                if text.startswith("```"):
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                audio_prompts = _json.loads(text)
                if not isinstance(audio_prompts, dict):
                    audio_prompts = {}
        except (_json.JSONDecodeError, AttributeError):
            for s in scenes[:12]:
                if isinstance(s, dict):
                    sid = str(s.get("id", "?"))
                    loc = s.get("location", "")
                    beat = s.get("emotional_beat", "neutral")
                    audio_prompts[sid] = f"Ambient atmosphere of {loc}. Emotional tone: {beat}. Cinematic soundscape."

        logger.info(
            f"[{self.agent_type}] Crafted audio prompts for {len(audio_prompts)} scenes"
        )

        return WorkResult(
            success=True,
            output_data={
                "audio_prompts": audio_prompts,
            },
            wall_time_ms=self.wall_time_ms,
            tokens_used=self.tokens_used,
        )
