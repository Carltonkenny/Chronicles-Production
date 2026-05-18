import logging
import asyncio
from pathlib import Path
from typing import Optional

logger = logging.getLogger("chronicles-edge-tts")

try:
    import edge_tts

    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False
    edge_tts = None

VOICE_MAP: dict[str, str] = {
    "roman": "en-US-EricNeural",
    "egyptian": "en-US-AriaNeural",
    "viking": "en-US-GuyNeural",
    "japanese": "ja-JP-NanamiNeural",
    "aztec": "en-US-JennyNeural",
    "mauryan": "en-IN-NeerjaNeural",
    "chola": "en-IN-NeerjaNeural",
    "mali_empire": "en-US-AriaNeural",
    "swahili_coast": "en-US-JennyNeural",
    "yoruba": "en-US-JennyNeural",
    "maya": "en-US-JennyNeural",
    "nazi_germany": "de-DE-KatjaNeural",
    "soviet_union": "ru-RU-SvetlanaNeural",
    "british_empire": "en-GB-SoniaNeural",
    "spanish_empire": "es-ES-ElviraNeural",
    "default": "en-US-AriaNeural",
}

CACHE_DIR = Path(__file__).parent / "audio_cache"
CACHE_DIR.mkdir(exist_ok=True)

_audio_cache: dict[str, bytes] = {}


def get_voice_for_culture(culture: str) -> str:
    return VOICE_MAP.get(culture, VOICE_MAP["default"])


def get_rate_for_beat(emotional_beat: str) -> str:
    rates = {
        "wonder_discovery": "-10%",
        "tension_fear": "+5%",
        "joy_connection": "+10%",
        "grief_loss": "-25%",
        "anger_confrontation": "+15%",
        "hope_determination": "+5%",
        "despair_hopelessness": "-20%",
        "love_vulnerability": "-10%",
        "suspense_anticipation": "-5%",
        "resolution_peace": "-15%",
    }
    return rates.get(emotional_beat, "+0%")


class EdgeTTSService:
    def __init__(self):
        self.available = HAS_EDGE_TTS
        if self.available:
            logger.info("Edge TTS initialized (free, unlimited)")
        else:
            logger.warning("Edge TTS not available. Install: pip install edge-tts")

    async def generate(
        self, text: str, voice: str = None, rate: str = "+0%", pitch: str = "+0Hz"
    ) -> Optional[bytes]:
        if not self.available:
            return None
        if not text or not text.strip():
            return None

        voice = voice or VOICE_MAP["default"]

        try:
            communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
            mp3_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    mp3_data += chunk["data"]
            logger.info(
                f"Edge TTS: {voice} rate={rate} pitch={pitch} -> {len(mp3_data)} bytes"
            )
            return mp3_data
        except Exception as e:
            logger.error(f"Edge TTS generation failed: {e}")
            return None

    async def narrate_scenes(
        self, scenes: list[dict], culture: str, theme: str
    ) -> Optional[bytes]:
        voice = get_voice_for_culture(culture)
        all_audio = b""

        for scene in scenes:
            text = scene.get("narration_text", scene.get("summary", ""))
            beat = scene.get("emotional_beat", "resolution_peace")
            rate = get_rate_for_beat(beat)

            audio = await self.generate(text=text, voice=voice, rate=rate)
            if audio:
                all_audio += audio

        if all_audio:
            logger.info(f"Narrated {len(scenes)} scenes -> {len(all_audio)} bytes")
            return all_audio
        return None

    async def narrate_story(
        self, title: str, story_text: str, culture: str, theme: str
    ) -> Optional[bytes]:
        voice = get_voice_for_culture(culture)
        script = f"{title}.\n\n{story_text}"
        return await self.generate(text=script, voice=voice, rate="-5%")

    def get_cached(self, story_hash: str) -> Optional[bytes]:
        cache_path = CACHE_DIR / f"{story_hash}.mp3"
        if cache_path.exists():
            return cache_path.read_bytes()
        return _audio_cache.get(story_hash)

    def cache(self, story_hash: str, audio_data: bytes) -> None:
        try:
            cache_path = CACHE_DIR / f"{story_hash}.mp3"
            cache_path.write_bytes(audio_data)
        except Exception:
            _audio_cache[story_hash] = audio_data


edge_tts_service = EdgeTTSService()
