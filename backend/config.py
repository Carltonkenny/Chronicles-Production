from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    POLLINATIONS_BASE_URL: str = "https://gen.pollinations.ai/v1/chat/completions"
    POLLINATIONS_MODEL: str = os.getenv("POLLINATIONS_MODEL", "gemini-fast")
    POLLINATIONS_API_KEY: str = os.getenv("POLLINATIONS_API_KEY", "")

    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1/chat/completions"
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "nousresearch/hermes-3-llama-3.1-405b:free")
    OPENROUTER_FALLBACK_MODEL: str = os.getenv("OPENROUTER_FALLBACK_MODEL", "meta-llama/llama-3.2-3b-instruct:free")

    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openrouter")

    MAX_STORY_WORDS: int = 800
    MIN_STORY_WORDS: int = 350

    PLANNER_TEMPERATURE: float = 0.92
    WRITER_TEMPERATURE: float = 0.75

    PLANNER_MAX_TOKENS: int = 3500
    WRITER_MAX_TOKENS: int = 3000

    REQUEST_TIMEOUT: int = 120
    MAX_RETRIES: int = 2

    AWS_REGION: str = os.getenv("AWS_REGION", "ap-southeast-1")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")

    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    MAX_CONCURRENT_LLM: int = 8
    MAX_CONCURRENT_VIDEO: int = 4
    AGENT_TIMEOUT_S: int = 30

    TARGET_FILM_DURATION_S: int = 90
    CLIP_DURATION_S: int = 8

    def validate(self) -> None:
        if not self.POLLINATIONS_MODEL:
            raise ValueError("POLLINATIONS_MODEL must be set in .env file")

    @property
    def headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.POLLINATIONS_API_KEY:
            headers["Authorization"] = f"Bearer {self.POLLINATIONS_API_KEY}"
        return headers


CONFIG = Config()
CONFIG.validate()


TIMELINE_BUCKETS: dict[str, str] = {
    "paleolithic": "ancient",
    "early_bronze_age": "ancient",
    "classical_antiquity": "ancient",
    "early_medieval": "medieval",
    "high_medieval": "medieval",
    "age_of_exploration": "early_modern",
    "world_war_era": "modern",
    "cold_war": "modern",
    "globalization": "contemporary",
    "polarization_era": "contemporary",
    "ai_hegemony": "near_future",
    "climate_migration": "near_future",
    "systemic_collapse": "collapse",
    "post_collapse_tribal": "collapse",
    "interplanetary_frontier": "space",
}

BUCKET_ORDER: list[str] = [
    "ancient",
    "medieval",
    "early_modern",
    "modern",
    "contemporary",
    "near_future",
    "collapse",
    "space",
]

CULTURE_NATURAL_ERA: dict[str, str] = {
    "roman": "ancient",
    "egyptian": "ancient",
    "mauryan": "ancient",
    "maya": "ancient",
    "viking": "medieval",
    "japanese": "medieval",
    "aztec": "medieval",
    "chola": "medieval",
    "mali_empire": "medieval",
    "swahili_coast": "medieval",
    "yoruba": "medieval",
    "spanish_empire": "early_modern",
    "british_empire": "early_modern",
    "nazi_germany": "modern",
    "soviet_union": "modern",
}

SAFETY_CONSTRAINED_CULTURES: dict[str, str] = {
    "nazi_germany": (
        "HARD RULE: No heroic Nazis. No propaganda tone. No ideology-as-aesthetic. "
        "POV MUST be victims, resistance, or civilian moral descent. "
        "Explicit in-story condemnation of the regime is mandatory."
    ),
    "british_empire": (
        "FORBID: white-savior defaults, benevolent colonizer framing, native-gratitude tropes. "
        "REQUIRED: at least one colonized-culture POV character, show systemic extraction not just individual villains."
    ),
    "spanish_empire": (
        "FORBID: white-savior defaults, civilizing-mission framing, native-gratitude tropes. "
        "REQUIRED: at least one indigenous POV character, show encomienda/systemic extraction costs."
    ),
}

TASK_MODELS: dict[str, str] = {
    "planner": "openrouter:nousresearch/hermes-3-llama-3.1-405b:free",
    "writer": "openrouter:nousresearch/hermes-3-llama-3.1-405b:free",
    "supervisor": "openrouter:meta-llama/llama-3.2-3b-instruct:free",
    "visuals": "openrouter:meta-llama/llama-3.2-3b-instruct:free",
    "default": "openrouter:nousresearch/hermes-3-llama-3.1-405b:free",
}
