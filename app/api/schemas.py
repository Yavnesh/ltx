from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr
from typing import Literal


class UserRegisterSchema(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")


class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str


class TokenSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"


class VideoJobCreateSchema(BaseModel):
    prompt: str = Field(..., max_length=1000, description="Text prompt describing the video to generate")
    duration: int = Field(5, ge=1, le=30, description="Video duration in seconds")
    resolution: Literal["360p", "480p", "720p"] = Field("720p", description="Video resolution")
    fps: int = Field(24, ge=8, le=30, description="Frames per second")
    seed: int = Field(123, ge=0, description="Random seed for video generator reproducibility")


class VideoJobResponseSchema(BaseModel):
    job_id: UUID = Field(..., alias="id")
    prompt: str
    duration: int
    resolution: str
    seed: int
    status: str
    video_url: str | None = None
    failure_reason: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    class Config:
        populate_by_name = True
        from_attributes = True


class VideoJobListResponseSchema(BaseModel):
    items: list[VideoJobResponseSchema]
    total: int
    limit: int
    offset: int
