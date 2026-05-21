import hashlib

from agents.base_agent import BaseAgent
from schemas import WorkOrder, WorkResult
from prompts.sound_designer_prompt import SOUND_DESIGNER_PROMPT
from utils.llm_client import call_llm
from logger_config import setup_logger

logger = setup_logger("SoundDesignerAgent")


class SoundDesignerAgent(BaseAgent):
    agent_type = "sound_designer"

    async def _execute_internal(self, work_order: WorkOrder) -> WorkResult:
        data = work_order.input_data
        narration_path = data.get("narration_path", "")
        culture = data.get("culture", "")
        scenes = data.get("scenes", [])

        emotional_beats = [s.get("emotional_beat", "neutral") for s in scenes if isinstance(s, dict)]

        scenes_text = ""
        for s in scenes[:12]:
            if isinstance(s, dict):
                scenes_text += f"Scene {s.get('id', '?')}: {s.get('summary', '')} [{s.get('location', '')}]\n"

        prompt = SOUND_DESIGNER_PROMPT.format(
            narration_path=narration_path or "/tmp/narration.mp3",
            culture=culture,
            scenes=scenes_text or "No scenes",
            emotional_beats=", ".join(emotional_beats) if emotional_beats else "neutral",
        )

        llm_result = await call_llm(
            system=SOUND_DESIGNER_PROMPT.split("## INPUT")[0],
            user=prompt,
            temperature=0.3,
            max_tokens=800,
            task="default",
        )

        self.tokens_used = 0

        import json as _json
        audio_timeline = {}
        try:
            if isinstance(llm_result, str):
                text = llm_result.strip()
                if text.startswith("```"):
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                audio_timeline = _json.loads(text)
        except (_json.JSONDecodeError, AttributeError):
            audio_timeline = {
                "narration": {
                    "audio_path": narration_path or "/tmp/narration.mp3",
                    "start_offset_s": 3.0,
                    "volume_db": 0.0,
                },
                "music": [],
                "ambience": [],
                "mix_spec": {
                    "music_volume_db": -15.0,
                    "ambience_volume_db": -18.0,
                    "crossfade_duration_s": 2.0,
                },
            }

        logger.info(f"[{self.agent_type}] Audio timeline created with narration at {audio_timeline.get('narration', {}).get('start_offset_s', 0)}s offset")

        return WorkResult(
            success=True,
            output_data={
                "audio_timeline": audio_timeline,
            },
            wall_time_ms=self.wall_time_ms,
            tokens_used=self.tokens_used,
        )
