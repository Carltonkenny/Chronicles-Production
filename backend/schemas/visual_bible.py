from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class ColorPalette(BaseModel):
    primary: List[str] = Field(default_factory=list, description="Primary hex colors")
    secondary: List[str] = Field(default_factory=list, description="Secondary hex colors")
    accent: List[str] = Field(default_factory=list, description="Accent hex colors")


class CharacterBible(BaseModel):
    name: str = Field(..., description="Character name")
    role: str = Field(..., description="Character role in story")
    appearance: str = Field(..., description="Detailed physical appearance")
    costume: str = Field(..., description="Culture-specific costume description")
    signature_items: List[str] = Field(default_factory=list, description="1-2 unique signature items")
    emotional_range: str = Field(default="", description="Emotional arc: wonder→obsession→remorse")
    portrait_prompt: Optional[str] = Field(default=None, description="Image generation prompt")


class LocationDescription(BaseModel):
    name: str = Field(..., description="Location identifier")
    description: str = Field(..., description="Rich visual description")
    materials: List[str] = Field(default_factory=list, description="Specific materials: limestone, oak, etc.")
    lighting: str = Field(..., description="Lighting description with source and quality")
    time_of_day: str = Field(default="day", description="Time of day")


class ShotVariation(BaseModel):
    shot_id: str = Field(..., description="Shot identifier per scene")
    shot_type: str = Field(..., description="Wide establishing, medium, close-up, etc.")
    focal_length: str = Field(..., description="35mm, 50mm, 85mm etc.")
    movement: str = Field(default="static", description="Static, slow push-in, dutch angle, etc.")
    description: str = Field(default="", description="What this shot captures")


class EmotionCameraMap(BaseModel):
    emotion: str = Field(..., description="wonder, obsession, remorse, fear, joy, grief")
    camera_style: str = Field(..., description="slow push-in shallow DOF, dutch angle tight framing, etc.")


class VisualElement(BaseModel):
    category: str = Field(..., description="clothing, architecture, artifact, lighting, hairstyle, color_palette")
    name: str = Field(..., description="Element name")
    description: str = Field(..., description="Rich cultural description")
    materials: List[str] = Field(default_factory=list, description="Materials used")
    colors: List[str] = Field(default_factory=list, description="Hex color codes or descriptive colors")


class VisualElementsDict(BaseModel):
    culture: str
    timeline: str
    clothing: List[VisualElement] = Field(default_factory=list)
    architecture: List[VisualElement] = Field(default_factory=list)
    artifact: List[VisualElement] = Field(default_factory=list)
    lighting: List[VisualElement] = Field(default_factory=list)
    hairstyle: List[VisualElement] = Field(default_factory=list)
    color_palette: List[VisualElement] = Field(default_factory=list)
    generated_by: str = Field(default="llm", description="llm, db_cache, redis_cache")


class VisualBible(BaseModel):
    story_hash: str = Field(..., description="Story hash this belongs to")
    film_tone: str = Field(default="", description="Dark brooding fire-lit, bright hopeful dawn, etc.")
    pacing: str = Field(default="", description="Slow discovery → frantic obsession → quiet resolution")
    color_palette: ColorPalette = Field(default_factory=ColorPalette)
    lighting_style: str = Field(default="", description="Overall lighting style across all scenes")
    character_bibles: List[CharacterBible] = Field(default_factory=list)
    location_descriptions: List[LocationDescription] = Field(default_factory=list)
    prop_list: List[str] = Field(default_factory=list, description="Key props per scene")
    shot_variation_matrix: Dict[str, List[ShotVariation]] = Field(default_factory=dict, description="scene_id → shots")
    emotion_camera_map: List[EmotionCameraMap] = Field(default_factory=list, description="Emotion → camera mapping")
    visual_elements: Optional[VisualElementsDict] = Field(default=None, description="Structured visual data from PD")
