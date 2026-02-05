"""MongoDB model helpers for raw_posts_data."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, constr

RAW_POSTS_COLLECTION = "raw_posts_data"
_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _now_str() -> str:
    return datetime.utcnow().strftime(_DATETIME_FORMAT)


@dataclass
class RawPostsDataModel:
    code: str
    name: str
    country: str
    dob: str
    excellence_field: str
    challenges_faced: str
    quote_created: bool = False
    posted: bool = False
    added_on: str = field(default_factory=_now_str)
    updated_on: str = field(default_factory=_now_str)
    quote_created_on: Optional[str] = None
    posted_on: Optional[str] = None

    def to_bson(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "country": self.country,
            "dob": self.dob,
            "excellence_field": self.excellence_field,
            "challenges_faced": self.challenges_faced,
            "quote_created": self.quote_created,
            "posted": self.posted,
            "added_on": self.added_on,
            "updated_on": self.updated_on,
            "quote_created_on": self.quote_created_on,
            "posted_on": self.posted_on,
        }

    @classmethod
    def from_bson(cls, doc: Dict[str, Any]) -> "RawPostsDataModel":
        return cls(
            code=doc.get("code", ""),
            name=doc.get("name", ""),
            country=doc.get("country", ""),
            dob=doc.get("dob", ""),
            excellence_field=doc.get("excellence_field", ""),
            challenges_faced=doc.get("challenges_faced", ""),
            quote_created=doc.get("quote_created", False),
            posted=doc.get("posted", False),
            added_on=doc.get("added_on", _now_str()),
            updated_on=doc.get("updated_on", _now_str()),
            quote_created_on=doc.get("quote_created_on"),
            posted_on=doc.get("posted_on"),
        )


class RawPostsDataSchema(BaseModel):
    code: str
    name: str
    country: str
    dob: str
    excellence_field: str
    challenges_faced: str
    quote_created: bool = False
    posted: bool = False
    added_on: str
    updated_on: str
    quote_created_on: Optional[str] = None
    posted_on: Optional[str] = None


class RawPostsDataResponse(BaseModel):
    id: str = Field(..., alias="_id")
    code: str
    name: str
    country: str
    dob: str
    excellence_field: str
    challenges_faced: str
    quote_created: bool = False
    posted: bool = False
    added_on: str
    updated_on: str
    quote_created_on: Optional[str] = None
    posted_on: Optional[str] = None

    class Config:
        allow_population_by_field_name = True
        populate_by_name = True


class RawPostsDataCreate(BaseModel):
    code: constr(strip_whitespace=True, min_length=1)
    name: constr(strip_whitespace=True, min_length=1)
    country: constr(strip_whitespace=True, min_length=1)
    dob: constr(strip_whitespace=True, min_length=1)
    excellence_field: constr(strip_whitespace=True, min_length=1)
    challenges_faced: constr(strip_whitespace=True, min_length=1)
    quote_created: Optional[bool] = None
    posted: Optional[bool] = None
    quote_created_on: Optional[str] = None
    posted_on: Optional[str] = None


class RawPostsDataUpdate(BaseModel):
    name: Optional[constr(strip_whitespace=True, min_length=1)] = None
    country: Optional[constr(strip_whitespace=True, min_length=1)] = None
    dob: Optional[constr(strip_whitespace=True, min_length=1)] = None
    excellence_field: Optional[constr(strip_whitespace=True, min_length=1)] = None
    challenges_faced: Optional[constr(strip_whitespace=True, min_length=1)] = None
    quote_created: Optional[bool] = None
    posted: Optional[bool] = None
    updated_on: Optional[str] = None
    quote_created_on: Optional[str] = None
    posted_on: Optional[str] = None
