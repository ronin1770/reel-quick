"""MongoDB model helpers for text overlay job status."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, constr

TEXT_OVERLAY_JOB_COLLECTION = "text_overlay_jobs"

TextOverlayJobStatus = Literal["pending", "progressing", "finished", "error"]


def _now_utc() -> datetime:
    return datetime.utcnow()


@dataclass
class TextOverlayJobModel:
    video_id: str
    status: TextOverlayJobStatus = "pending"
    status_message: Optional[str] = None
    arq_job_id: Optional[str] = None
    created_at: datetime = field(default_factory=_now_utc)
    updated_at: datetime = field(default_factory=_now_utc)

    def to_bson(self) -> Dict[str, Any]:
        return {
            "video_id": self.video_id,
            "status": self.status,
            "status_message": self.status_message,
            "arq_job_id": self.arq_job_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_bson(cls, doc: Dict[str, Any]) -> "TextOverlayJobModel":
        return cls(
            video_id=doc.get("video_id", ""),
            status=doc.get("status", "pending"),
            status_message=doc.get("status_message"),
            arq_job_id=doc.get("arq_job_id"),
            created_at=doc.get("created_at", _now_utc()),
            updated_at=doc.get("updated_at", _now_utc()),
        )


class TextOverlayJobSchema(BaseModel):
    video_id: str
    status: TextOverlayJobStatus = "pending"
    status_message: Optional[str] = None
    arq_job_id: Optional[str] = None
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)


class TextOverlayEnqueueRequest(BaseModel):
    video_id: constr(strip_whitespace=True, min_length=1)


class TextOverlayEnqueueResponse(BaseModel):
    message: str
    video_id: str
    job_id: str
    status: TextOverlayJobStatus
