"""MongoDB model helpers for videos."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, constr

VIDEO_COLLECTION = "videos"


@dataclass
class VideoModel:
    video_id: str
    video_title: str

    # NOTE: In your DB / API responses this is often a duration string like "00:00:06".
    # So keep it as Optional[str] to avoid response_model validation failures.
    video_size: Optional[str] = None

    video_introduction: Optional[str] = None
    creation_time: datetime = field(default_factory=datetime.utcnow)
    modification_time: datetime = field(default_factory=datetime.utcnow)
    active: bool = True
    video_tags: List[str] = field(default_factory=list)

    status: str = "created"
    output_file_location: Optional[str] = None
    job_id: Optional[str] = None
    error_reason: Optional[str] = None

    def to_bson(self) -> Dict[str, Any]:
        return {
            "video_id": self.video_id,
            "video_title": self.video_title,
            "video_size": self.video_size,
            "video_introduction": self.video_introduction,
            "creation_time": self.creation_time,
            "modification_time": self.modification_time,
            "active": self.active,
            "video_tags": list(self.video_tags),
            "status": self.status,
            "output_file_location": self.output_file_location,
            "job_id": self.job_id,
            "error_reason": self.error_reason,
        }

    @classmethod
    def from_bson(cls, doc: Dict[str, Any]) -> "VideoModel":
        return cls(
            video_id=doc.get("video_id", ""),
            video_title=doc.get("video_title", ""),
            video_size=doc.get("video_size"),
            video_introduction=doc.get("video_introduction"),
            creation_time=doc.get("creation_time", datetime.utcnow()),
            modification_time=doc.get("modification_time", datetime.utcnow()),
            active=doc.get("active", True),
            video_tags=doc.get("video_tags", []) or [],
            status=doc.get("status", "created"),
            output_file_location=doc.get("output_file_location"),
            job_id=doc.get("job_id"),
            error_reason=doc.get("error_reason"),
        )


class VideoSchema(BaseModel):
    video_id: str
    video_title: str
    video_size: Optional[str] = None
    video_introduction: Optional[str] = None
    creation_time: datetime = Field(default_factory=datetime.utcnow)
    modification_time: datetime = Field(default_factory=datetime.utcnow)
    active: bool = True
    video_tags: List[str] = Field(default_factory=list)
    status: str = "created"
    output_file_location: Optional[str] = None
    job_id: Optional[str] = None
    error_reason: Optional[str] = None


class VideoCreate(BaseModel):
    video_title: constr(strip_whitespace=True, min_length=1)
    video_size: Optional[str] = None
    video_introduction: Optional[str] = None
    active: Optional[bool] = None
    video_tags: Optional[List[str]] = None


class VideoUpdate(BaseModel):
    # PATCH should be partial updates, so everything here should be Optional.
    video_title: Optional[constr(strip_whitespace=True, min_length=1)] = None
    video_size: Optional[str] = None
    video_introduction: Optional[str] = None
    active: Optional[bool] = None
    video_tags: Optional[List[str]] = None
