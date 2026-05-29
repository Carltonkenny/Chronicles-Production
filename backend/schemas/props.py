from pydantic import BaseModel, Field
from typing import Literal, Optional


class PropDetail(BaseModel):
    name: str = Field(..., description="Prop name")
    prop_type: Literal[
        "weapon", "jewelry", "vehicle", "tool", "furniture", "accessory", "religious",
    ] = Field(..., description="Category of prop")
    materials: list[str] = Field(default_factory=list)
    dimensions: str = Field(default="", description='e.g. "12-inch blade", "6-foot tall"')
    colors: list[str] = Field(default_factory=list, description="Hex color codes")
    era_name: str = Field(default="", description="Culture/timeline era")
    character_owner: Optional[str] = Field(default=None, description="Which character owns this prop")
    scene_used_in: list[str] = Field(default_factory=list, description="Scene IDs where prop appears")
    cultural_significance: str = Field(default="", description="Why this prop matters in this culture")
