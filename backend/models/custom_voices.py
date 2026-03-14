"""MongoDB model helpers for custom voices."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, constr

CUSTOM_VOICES_COLLECTION = "custom_voices"


def _now_utc() -> datetime:
    return datetime.utcnow()


@dataclass
class CustomVoiceModel:
    request_id: str
    voice_name: str
    instructions: str
    output_file_location: Optional[str] = None
    created_at: datetime = field(default_factory=_now_utc)
    updated_at: datetime = field(default_factory=_now_utc)

    def to_bson(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "voice_name": self.voice_name,
            "instructions": self.instructions,
            "output_file_location": self.output_file_location,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_bson(cls, doc: Dict[str, Any]) -> "CustomVoiceModel":
        return cls(
            request_id=doc.get("request_id", ""),
            voice_name=doc.get("voice_name", ""),
            instructions=doc.get("instructions", ""),
            output_file_location=doc.get("output_file_location"),
            created_at=doc.get("created_at", _now_utc()),
            updated_at=doc.get("updated_at", _now_utc()),
        )


class CustomVoiceSchema(BaseModel):
    request_id: str
    voice_name: str
    instructions: str
    output_file_location: Optional[str] = None
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)


class CustomVoiceCreate(BaseModel):
    request_id: constr(strip_whitespace=True, min_length=1)
    voice_name: constr(strip_whitespace=True, min_length=1)
    instructions: constr(strip_whitespace=True, min_length=1)
    output_file_location: Optional[str] = None


class CustomVoiceUpdate(BaseModel):
    voice_name: Optional[constr(strip_whitespace=True, min_length=1)] = None
    instructions: Optional[constr(strip_whitespace=True, min_length=1)] = None
    output_file_location: Optional[str] = None
    updated_at: Optional[datetime] = None
