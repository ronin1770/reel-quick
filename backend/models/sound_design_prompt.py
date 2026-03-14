"""MongoDB model helpers for sound design prompt requests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, constr

SOUND_DESIGN_PROMPT_COLLECTION = "sound_design_prompt"

SoundDesignPromptStatus = Literal["passed", "failed"]


def _now_utc() -> datetime:
    return datetime.utcnow()


@dataclass
class SoundDesignPromptModel:
    sound_design_id: str
    status: SoundDesignPromptStatus
    request_payload: Dict[str, Any]
    response_payload: Dict[str, Any]
    text: str
    custom_voice_text: str = ""
    language: Optional[str] = None
    preset_name: Optional[str] = None
    request_id: Optional[str] = None
    derived_instruction: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=_now_utc)
    updated_at: datetime = field(default_factory=_now_utc)

    def to_bson(self) -> Dict[str, Any]:
        return {
            "sound_design_id": self.sound_design_id,
            "status": self.status,
            "request_payload": self.request_payload,
            "response_payload": self.response_payload,
            "text": self.text,
            "custom_voice_text": self.custom_voice_text,
            "language": self.language,
            "preset_name": self.preset_name,
            "request_id": self.request_id,
            "derived_instruction": self.derived_instruction,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_bson(cls, doc: Dict[str, Any]) -> "SoundDesignPromptModel":
        return cls(
            sound_design_id=doc.get("sound_design_id", ""),
            status=doc.get("status", "failed"),
            request_payload=doc.get("request_payload", {}),
            response_payload=doc.get("response_payload", {}),
            text=doc.get("text", ""),
            custom_voice_text=doc.get("custom_voice_text", ""),
            language=doc.get("language"),
            preset_name=doc.get("preset_name"),
            request_id=doc.get("request_id"),
            derived_instruction=doc.get("derived_instruction"),
            error_code=doc.get("error_code"),
            error_message=doc.get("error_message"),
            created_at=doc.get("created_at", _now_utc()),
            updated_at=doc.get("updated_at", _now_utc()),
        )


class SoundDesignPromptSchema(BaseModel):
    sound_design_id: str
    status: SoundDesignPromptStatus
    request_payload: Dict[str, Any]
    response_payload: Dict[str, Any]
    text: str
    custom_voice_text: str = ""
    language: Optional[str] = None
    preset_name: Optional[str] = None
    request_id: Optional[str] = None
    derived_instruction: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)


class SoundDesignPromptCreate(BaseModel):
    sound_design_id: constr(strip_whitespace=True, min_length=1)
    status: SoundDesignPromptStatus
    request_payload: Dict[str, Any] = Field(default_factory=dict)
    response_payload: Dict[str, Any] = Field(default_factory=dict)
    text: constr(strip_whitespace=True, min_length=1)
    custom_voice_text: Optional[constr(strip_whitespace=True, min_length=1)] = None
    language: Optional[str] = None
    preset_name: Optional[str] = None
    request_id: Optional[str] = None
    derived_instruction: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class SoundDesignPromptUpdate(BaseModel):
    status: Optional[SoundDesignPromptStatus] = None
    response_payload: Optional[Dict[str, Any]] = None
    custom_voice_text: Optional[constr(strip_whitespace=True, min_length=1)] = None
    request_id: Optional[str] = None
    derived_instruction: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    updated_at: Optional[datetime] = None
