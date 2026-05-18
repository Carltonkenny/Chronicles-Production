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
