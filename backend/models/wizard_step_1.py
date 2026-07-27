"""MongoDB model helpers for Instagram Reel wizard Step 1 research."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, constr

WIZARD_STEP_1_COLLECTION = "wizard_step_1"
WIZARD_STATUS_DRAFT = "draft"
WIZARD_STATUS_RUNNING = "running"
WIZARD_STATUS_COMPLETED = "completed"
WIZARD_STATUS_FAILED = "failed"
DEFAULT_WIZARD_LANGUAGE = "English"
DEFAULT_WIZARD_PLATFORM = "Instagram Reels"
DEFAULT_TREND_LIMIT = 20
MIN_TREND_COUNT = 5
DEFAULT_EXAMPLE_ITEM_LIMIT = 5
_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _now_str() -> str:
    return datetime.utcnow().strftime(_DATETIME_FORMAT)


@dataclass
class Step1WizardModel:
    niche: str
    research_period: Dict[str, str]
    language: str = DEFAULT_WIZARD_LANGUAGE
    platforms_analyzed: List[str] = field(
        default_factory=lambda: [DEFAULT_WIZARD_PLATFORM]
    )
    trend_limit: int = DEFAULT_TREND_LIMIT
    status: str = WIZARD_STATUS_DRAFT
    research_result_json: Optional[Dict[str, Any]] = None
    debug_raw_response: Optional[str] = None
    debug_validation_errors: Optional[List[Dict[str, Any]]] = None
    created_at: str = field(default_factory=_now_str)
    updated_at: str = field(default_factory=_now_str)
    completed_at: Optional[str] = None
    failed_at: Optional[str] = None

    def to_bson(self) -> Dict[str, Any]:
        return {
            "niche": self.niche,
            "research_period": dict(self.research_period),
            "language": self.language,
            "platforms_analyzed": list(self.platforms_analyzed),
            "trend_limit": self.trend_limit,
            "status": self.status,
            "research_result_json": self.research_result_json,
            "debug_raw_response": self.debug_raw_response,
            "debug_validation_errors": self.debug_validation_errors,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "failed_at": self.failed_at,
        }


class Step1ResearchPeriodSchema(BaseModel):
    start_date: str
    end_date: str


class Step1TrendSchema(BaseModel):
    trend_id: Optional[str] = None
    trend_name: str
    summary: str
    evidence: str
    opportunity_score: int
    creator_guidance: str
    example_hooks: List[str]
    example_titles: List[str]
    example_video_concepts: List[str]
    recommended_video_structure: List[str]
    suggested_visual_style: List[str]
    risks_and_limitations: List[str]


class Step1ResearchResultSchema(BaseModel):
    wizard_id: str
    niche: str
    language: str
    research_period: Step1ResearchPeriodSchema
    platforms_analyzed: List[str]
    trends: List[Step1TrendSchema]


class Step1WizardResponse(BaseModel):
    id: str = Field(..., alias="_id")
    niche: str
    research_period: Step1ResearchPeriodSchema
    language: str
    platforms_analyzed: List[str]
    trend_limit: int
    status: str
    research_result_json: Optional[Dict[str, Any]] = None
    debug_raw_response: Optional[str] = None
    debug_validation_errors: Optional[List[Dict[str, Any]]] = None
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    failed_at: Optional[str] = None


class Step1WizardCreate(BaseModel):
    niche: constr(strip_whitespace=True, min_length=1)
    start_date: constr(strip_whitespace=True, min_length=1)
    end_date: constr(strip_whitespace=True, min_length=1)
    language: Optional[constr(strip_whitespace=True, min_length=1)] = None
    trend_limit: Optional[int] = None
