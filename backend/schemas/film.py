from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class FilmStatus(str, Enum):
    PENDING = "pending"
    STORY_GENERATING = "story_generating"
    VISUAL_BIBLE_CREATING = "visual_bible_creating"
    IMAGES_GENERATING = "images_generating"
    VIDEO_GENERATING = "video_generating"
    POST_PROCESSING = "post_processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FilmSummary(BaseModel):
    story_hash: str
    title: str
    culture: str
    timeline: str
    theme: str
    mode: str
    thumbnail_url: Optional[str] = None
    duration: int = 90
    created_at: str


class CatalogRow(BaseModel):
    id: str
    title: str
    type: str
    films: List[FilmSummary]


class CatalogResponse(BaseModel):
    films: List[FilmSummary]
    rows: List[CatalogRow]


class FilmDetail(BaseModel):
    story_hash: str
    title: str
    seed_idea: str
    culture: str
    timeline: str
    theme: str
    mode: str
    setting: Optional[str] = None
    narrative: Optional[str] = None
    theme_reflection: Optional[str] = None
    word_count: int = 0
    character_portraits: List[str] = []
    scene_images: List[str] = []
    video_url: Optional[str] = None
    narration_url: Optional[str] = None
    agent_count: int = 0
    generation_time_ms: int = 0
    created_at: str


class FilmOutput(BaseModel):
    film_id: str = Field(..., description="Unique film ID")
    story_hash: str = Field(..., description="Story hash")
    status: FilmStatus = Field(..., description="Current status")
    title: str = Field(..., description="Film title")
    duration_seconds: float = Field(default=0.0, description="Film duration")
    video_url: Optional[str] = Field(default=None, description="MP4 video URL")
    thumbnail_url: Optional[str] = Field(default=None, description="Thumbnail image URL")
    character_portraits: List[str] = Field(default_factory=list, description="Character portrait URLs")
    scene_images: List[str] = Field(default_factory=list, description="Scene keyframe URLs")
    narration_url: Optional[str] = Field(default=None, description="Narration audio URL")
    music_url: Optional[str] = Field(default=None, description="Background music URL")
    error_message: Optional[str] = Field(default=None, description="Error if failed")
    created_at: str = Field(..., description="Creation timestamp")
    completed_at: Optional[str] = Field(default=None, description="Completion timestamp")
