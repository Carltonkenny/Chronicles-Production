from pydantic import BaseModel, Field
from typing import Optional, List


class ImageResult(BaseModel):
    url: str = Field(..., description="Pollinations image URL")
    prompt: str = Field(..., description="Full prompt used for generation")
    seed: int = Field(..., description="Deterministic seed")
    variation: str = Field(default="full_body", description="full_body, close_up, action")
    orientation: str = Field(default="landscape", description="portrait or landscape")
    scene_id: Optional[str] = Field(default=None, description="Scene identifier if scene image")
    character: Optional[str] = Field(default=None, description="Character name if portrait")
    source: str = Field(default="generated", description="generated, cached, fallback")


class ImageOutput(BaseModel):
    story_hash: str = Field(..., description="Story hash")
    portraits: List[ImageResult] = Field(default_factory=list, description="All character portraits")
    scenes: List[ImageResult] = Field(default_factory=list, description="All scene keyframes")
    total_count: int = Field(default=0, description="Total images generated")
    wall_time_ms: float = Field(default=0.0, description="Total generation time")
    character_map: dict = Field(default_factory=dict, description="character_name → [ImageResult]")
