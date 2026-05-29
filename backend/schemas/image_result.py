from pydantic import BaseModel, Field
from typing import Optional, List, Literal

VariationType = Literal[
    "full_body", "close_up", "action", "scene_keyframe",
    "turnaround_sheet", "mugshot", "character_sheet",
    "physique_chart", "feature_closeup",
    "prop_image", "environment_asset",
    "establishing_shot", "action_shot",
    "emotional_closeup", "world_detail", "transition_shot",
]


class ImageResult(BaseModel):
    url: str = Field(..., description="Pollinations image URL")
    prompt: str = Field(..., description="Full prompt used for generation")
    seed: int = Field(..., description="Deterministic seed")
    variation: VariationType = Field(default="full_body")
    orientation: str = Field(default="landscape", description="portrait, landscape, or square")
    scene_id: Optional[str] = Field(default=None, description="Scene identifier if scene image")
    character: Optional[str] = Field(default=None, description="Character name if portrait")
    source: str = Field(default="generated", description="generated, cached, fallback")


class PropImageResult(BaseModel):
    url: str = Field(..., description="Prop image URL")
    prompt: str = Field(..., description="Full prompt used")
    seed: int = Field(..., description="Deterministic seed")
    prop_name: str = Field(..., description="Prop name")
    prop_type: str = Field(default="", description="weapon, jewelry, vehicle, tool, furniture, accessory, religious")
    materials: List[str] = Field(default_factory=list)
    character_owner: Optional[str] = Field(default=None, description="Owning character")
    source: str = Field(default="generated", description="generated, cached, fallback")


class ImageOutput(BaseModel):
    story_hash: str = Field(..., description="Story hash")
    portraits: List[ImageResult] = Field(default_factory=list, description="All character portraits")
    scenes: List[ImageResult] = Field(default_factory=list, description="All scene keyframes")
    props: List[PropImageResult] = Field(default_factory=list, description="All prop images")
    character_designs: List[ImageResult] = Field(default_factory=list, description="Turnaround sheets and design images")
    total_count: int = Field(default=0, description="Total images generated")
    wall_time_ms: float = Field(default=0.0, description="Total generation time")
    character_map: dict = Field(default_factory=dict, description="character_name -> [ImageResult]")
