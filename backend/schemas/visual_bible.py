from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class ColorPalette(BaseModel):
    primary: List[str] = Field(default_factory=list, description="Primary colors (hex)")
    secondary: List[str] = Field(default_factory=list, description="Secondary colors (hex)")
    accent: List[str] = Field(default_factory=list, description="Accent colors (hex)")


class CharacterBible(BaseModel):
    name: str = Field(..., description="Character name")
    role: str = Field(..., description="Character role")
    appearance: str = Field(..., description="Physical appearance description")
    costume: str = Field(..., description="Costume description")
    signature_items: List[str] = Field(default_factory=list, description="Signature items they carry")
    personality_traits: List[str] = Field(default_factory=list, description="Personality traits")
    portrait_prompt: Optional[str] = Field(default=None, description="Image generation prompt")


class LocationDescription(BaseModel):
    name: str = Field(..., description="Location name")
    description: str = Field(..., description="Detailed description")
    materials: List[str] = Field(default_factory=list, description="Materials used")
    lighting: str = Field(..., description="Lighting description")
    camera_angles: List[str] = Field(default_factory=list, description="Suggested camera angles")


class CameraLanguage(BaseModel):
    shot_type: str = Field(..., description="Shot type (wide, medium, close-up)")
    movement: str = Field(..., description="Camera movement (static, pan, dolly)")
    focal_length: str = Field(..., description="Focal length description")
    rhythm: str = Field(..., description="Editing rhythm")


class VisualBible(BaseModel):
    story_hash: str = Field(..., description="Story hash this belongs to")
    color_palette: ColorPalette = Field(..., description="Color palette")
    lighting_style: str = Field(..., description="Overall lighting style")
    camera_language: CameraLanguage = Field(..., description="Camera language")
    character_bibles: List[CharacterBible] = Field(default_factory=list, description="Character bibles")
    location_descriptions: List[LocationDescription] = Field(default_factory=list, description="Location descriptions")
    prop_list: List[str] = Field(default_factory=list, description="Props per scene")
    emotional_arc_to_camera_map: Dict[str, str] = Field(default_factory=dict, description="Emotion to camera mapping")
