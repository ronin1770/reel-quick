"""MongoDB model helpers for Instagram Reel wizard Step 2 video search."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, constr

STEP_2_COLLECTION = "step_2"
STEP_2_STATUS_PENDING = "pending"
STEP_2_STATUS_PROCESSING = "processing"
STEP_2_STATUS_COMPLETED = "completed"
STEP_2_STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
STEP_2_STATUS_FAILED = "failed"
DEFAULT_STEP_2_MAX_RESULTS = 10
MIN_STEP_2_MAX_RESULTS = 1
ALLOWED_STEP_2_ORIENTATIONS = ("vertical", "horizontal", "square", "unknown")
_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _now_str() -> str:
    return datetime.utcnow().strftime(_DATETIME_FORMAT)


@dataclass
class Step2WizardModel:
    wizard_id: str
    niche: str
    trend_name: str
    video_title: str
    video_concept: str
    maximum_results: int = DEFAULT_STEP_2_MAX_RESULTS
    status: str = STEP_2_STATUS_PENDING
    research_result_json: Optional[Dict[str, Any]] = None
    debug_raw_response: Optional[str] = None
    debug_validation_errors: Optional[List[Dict[str, Any]]] = None
    created_at: str = field(default_factory=_now_str)
    updated_at: str = field(default_factory=_now_str)
    completed_at: Optional[str] = None
    failed_at: Optional[str] = None

    def to_bson(self) -> Dict[str, Any]:
        return {
            "wizard_id": self.wizard_id,
            "niche": self.niche,
            "trend_name": self.trend_name,
            "video_title": self.video_title,
            "video_concept": self.video_concept,
            "maximum_results": self.maximum_results,
            "status": self.status,
            "research_result_json": self.research_result_json,
            "debug_raw_response": self.debug_raw_response,
            "debug_validation_errors": self.debug_validation_errors,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "failed_at": self.failed_at,
        }


class Step2QuerySchema(BaseModel):
    niche: constr(strip_whitespace=True, min_length=1)
    trend_name: constr(strip_whitespace=True, min_length=1)
    video_title: constr(strip_whitespace=True, min_length=1)
    video_concept: constr(strip_whitespace=True, min_length=1)
    maximum_results: int


class Step2LicenseSchema(BaseModel):
    license_name: constr(strip_whitespace=True, min_length=1)
    license_url: Optional[str] = None
    commercial_use_allowed: bool
    modification_allowed: bool
    attribution_required: bool
    license_verified: bool
    verification_notes: constr(strip_whitespace=True, min_length=1)


class Step2VideoResultSchema(BaseModel):
    result_id: constr(strip_whitespace=True, min_length=1)
    title: constr(strip_whitespace=True, min_length=1)
    description: constr(strip_whitespace=True, min_length=1)
    source: constr(strip_whitespace=True, min_length=1)
    page_url: constr(strip_whitespace=True, min_length=1)
    preview_url: Optional[str] = None
    creator_name: Optional[str] = None
    duration_seconds: Optional[float] = None
    orientation: Literal["vertical", "horizontal", "square", "unknown"]
    resolution: Optional[str] = None
    search_term: constr(strip_whitespace=True, min_length=1)
    visual_tags: List[constr(strip_whitespace=True, min_length=1)]
    recommended_usage: constr(strip_whitespace=True, min_length=1)
    license: Step2LicenseSchema
    relevance_score: int
    selection_notes: constr(strip_whitespace=True, min_length=1)


class Step2ResearchResultSchema(BaseModel):
    wizard_id: constr(strip_whitespace=True, min_length=1)
    query: Step2QuerySchema
    search_terms: List[constr(strip_whitespace=True, min_length=1)]
    videos: List[Step2VideoResultSchema]
    warnings: List[constr(strip_whitespace=True, min_length=1)]
    generated_at: constr(strip_whitespace=True, min_length=1)


class Step2WizardResponse(BaseModel):
    id: str = Field(..., alias="_id")
    wizard_id: str
    niche: str
    trend_name: str
    video_title: str
    video_concept: str
    maximum_results: int
    status: str
    research_result_json: Optional[Dict[str, Any]] = None
    debug_raw_response: Optional[str] = None
    debug_validation_errors: Optional[List[Dict[str, Any]]] = None
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    failed_at: Optional[str] = None


class Step2WizardCreate(BaseModel):
    trend_name: constr(strip_whitespace=True, min_length=1)
    video_title: constr(strip_whitespace=True, min_length=1)
    video_concept: constr(strip_whitespace=True, min_length=1)
    maximum_results: Optional[int] = None
