from pydantic import BaseModel, Field
from typing import Optional, List
from .enums import Culture, Timeline, Theme


class StoryRequest(BaseModel):
    seed_idea: str = Field(min_length=10, max_length=200, description="Core story concept")
    timeline: Timeline
    culture: Culture
    theme: Theme

    class Config:
        use_enum_values = False


class StoryOutput(BaseModel):
    title: str = Field(min_length=1, description="Story title")
    setting: str = Field(min_length=10, description="Evocative setting description")
    characters: List[str] = Field(default_factory=list, description="List of characters")
    story: str = Field(min_length=50, description="The story narrative")
    theme_reflection: str = Field(default="", min_length=0, description="Theme reflection")
    stereotypes_flagged: List[str] = Field(default_factory=list, description="Flagged stereotypes")
    validation_seed: bool = Field(default=True, description="Seed incorporated in blueprint")
    validation_theme: bool = Field(default=True, description="Theme demonstrated")


class StoryGenerationRequest(BaseModel):
    seed_idea: str = Field(min_length=10, max_length=200)
    culture: str
    timeline: str
    theme: str


class StoryGenerationResponse(BaseModel):
    success: bool
    title: str
    setting: str
    characters: List[str]
    story: str
    theme_reflection: str
    stereotypes_flagged: List[str]
    word_count: int
    metadata: dict
