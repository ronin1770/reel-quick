"""MongoDB model helpers for available video transitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, constr

AVAILABLE_TRANSITIONS_COLLECTION = "available_transitions"


@dataclass
class AvailableTransitionModel:
    id: str
    name: str
    active: bool = True
    date_added: datetime = field(default_factory=datetime.utcnow)
    date_updated: datetime = field(default_factory=datetime.utcnow)

    def to_bson(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "active": self.active,
            "date_added": self.date_added,
            "date_updated": self.date_updated,
        }

    @classmethod
    def from_bson(cls, doc: Dict[str, Any]) -> "AvailableTransitionModel":
        return cls(
            id=doc.get("id", ""),
            name=doc.get("name", ""),
            active=doc.get("active", True),
            date_added=doc.get("date_added", datetime.utcnow()),
            date_updated=doc.get("date_updated", datetime.utcnow()),
        )


class AvailableTransitionSchema(BaseModel):
    id: str
    name: str
    active: bool = True
    date_added: datetime = Field(default_factory=datetime.utcnow)
    date_updated: datetime = Field(default_factory=datetime.utcnow)


class AvailableTransitionCreate(BaseModel):
    id: Optional[constr(strip_whitespace=True, min_length=1)] = None
    name: constr(strip_whitespace=True, min_length=1)
    active: Optional[bool] = None


class AvailableTransitionUpdate(BaseModel):
    name: Optional[constr(strip_whitespace=True, min_length=1)] = None
    active: Optional[bool] = None
