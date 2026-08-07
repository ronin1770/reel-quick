"""MongoDB model helpers for Instagram Reel wizard Step 3 audio research."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, conint, constr

AUDIO_SEARCH_COLLECTION = "wizard_audio_search"
AUDIO_SEARCH_STATUS_PENDING = "pending"
AUDIO_SEARCH_STATUS_PROCESSING = "processing"
AUDIO_SEARCH_STATUS_COMPLETED = "completed"
AUDIO_SEARCH_STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
AUDIO_SEARCH_STATUS_FAILED = "failed"
DEFAULT_AUDIO_SEARCH_MAX_RESULTS = 10
MIN_AUDIO_SEARCH_MAX_RESULTS = 1
ALLOWED_AUDIO_TYPES = (
    "song",
    "instrumental",
    "remix",
    "original_audio",
    "voiceover",
)
ALLOWED_EVIDENCE_SOURCE_TYPES = (
    "trend_report",
    "instagram_audio_page",
    "instagram_reel",
    "article",
    "trend_platform",
)
_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _now_str() -> str:
    return datetime.utcnow().strftime(_DATETIME_FORMAT)


@dataclass
class AudioSearchWizardModel:
    wizard_id: str
    niche: str
    research_period: Dict[str, str]
    maximum_results: int = DEFAULT_AUDIO_SEARCH_MAX_RESULTS
    status: str = AUDIO_SEARCH_STATUS_PENDING
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
            "research_period": dict(self.research_period),
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


class AudioSearchResearchPeriodSchema(BaseModel):
    start_date: constr(strip_whitespace=True, min_length=1)
    end_date: constr(strip_whitespace=True, min_length=1)


class AudioSearchQuerySchema(BaseModel):
    niche: constr(strip_whitespace=True, min_length=1)
    start_date: constr(strip_whitespace=True, min_length=1)
    end_date: constr(strip_whitespace=True, min_length=1)
    maximum_results: conint(ge=MIN_AUDIO_SEARCH_MAX_RESULTS)


class AudioSearchInputValuesSchema(BaseModel):
    niche: constr(strip_whitespace=True, min_length=1)
    start_date: constr(strip_whitespace=True, min_length=1)
    end_date: constr(strip_whitespace=True, min_length=1)
    limit: conint(ge=MIN_AUDIO_SEARCH_MAX_RESULTS)


class AudioSearchEvidenceSchema(BaseModel):
    source_name: constr(strip_whitespace=True, min_length=1)
    source_type: Literal[
        "trend_report",
        "instagram_audio_page",
        "instagram_reel",
        "article",
        "trend_platform",
    ]
    published_or_updated_date: Optional[str] = None
    url: constr(strip_whitespace=True, min_length=1)
    supports: constr(strip_whitespace=True, min_length=1)


class AudioSearchRecommendationSchema(BaseModel):
    rank: conint(ge=1)
    audio_name: constr(strip_whitespace=True, min_length=1)
    artist_name: constr(strip_whitespace=True, min_length=1)
    audio_type: Literal[
        "song",
        "instrumental",
        "remix",
        "original_audio",
        "voiceover",
    ]
    relevance_score: conint(ge=0, le=100)
    trend_confidence_score: conint(ge=0, le=100)
    why_selected: constr(strip_whitespace=True, min_length=1)
    best_for: List[constr(strip_whitespace=True, min_length=1)] = Field(
        default_factory=list
    )
    evidence: List[AudioSearchEvidenceSchema] = Field(default_factory=list)


class AudioSearchModelResultSchema(BaseModel):
    niche: constr(strip_whitespace=True, min_length=1)
    research_period: AudioSearchResearchPeriodSchema
    generated_at: constr(strip_whitespace=True, min_length=1)
    results: List[AudioSearchRecommendationSchema] = Field(default_factory=list)
    limitations: List[constr(strip_whitespace=True, min_length=1)] = Field(
        default_factory=list
    )


class AudioSearchResearchResultSchema(BaseModel):
    wizard_id: constr(strip_whitespace=True, min_length=1)
    query: AudioSearchQuerySchema
    input_values: AudioSearchInputValuesSchema
    audio: AudioSearchModelResultSchema


class AudioSearchWizardResponse(BaseModel):
    id: str = Field(..., alias="_id")
    wizard_id: str
    niche: str
    research_period: AudioSearchResearchPeriodSchema
    maximum_results: int
    status: str
    research_result_json: Optional[Dict[str, Any]] = None
    debug_raw_response: Optional[str] = None
    debug_validation_errors: Optional[List[Dict[str, Any]]] = None
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    failed_at: Optional[str] = None


class AudioSearchWizardCreate(BaseModel):
    niche: constr(strip_whitespace=True, min_length=1)
    start_date: constr(strip_whitespace=True, min_length=1)
    end_date: constr(strip_whitespace=True, min_length=1)
    limit: Optional[int] = None
