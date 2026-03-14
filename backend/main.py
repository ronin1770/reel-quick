"""FastAPI entrypoint."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from arq import create_pool
from arq.connections import RedisSettings
from bson import ObjectId
from bson.errors import InvalidId
from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, Response, UploadFile, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, ValidationError
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from db import get_db, init_db
from logger import get_logger
from objects.prompt_constants import AI_TYPE_PROMPT_MAP, AI_TYPE_REQUIRED_FIELDS, AI_TYPES
from objects.sound_prompt_creator import (
    SoundPromptCreator,
    VoiceProfile as SoundPromptVoiceProfile,
)
from objects.sound_prompt_preset import SoundPromptPreset
from models.person_bio import PERSON_BIO_COLLECTION
from models.quotes import QUOTES_COLLECTION
from models.raw_posts_data import (
    RAW_POSTS_COLLECTION,
    RawPostsDataCreate,
    RawPostsDataModel,
    RawPostsDataResponse,
    RawPostsDataUpdate,
    _now_str,
)
from models.sound_design_prompt import (
    SOUND_DESIGN_PROMPT_COLLECTION,
    SoundDesignPromptModel,
    SoundDesignPromptStatus,
)
from models.custom_voices import CUSTOM_VOICES_COLLECTION
from models.video_model import VideoCreate, VideoSchema, VideoUpdate
from models.voice_job_status import VOICE_CLONE_JOB_COLLECTION, VoiceCloneJobModel
from models.video_part_model import (
    VideoPartCreate,
    VideoPartSchema,
    VideoPartUpdate,
)
from workers.queue_names import (
    AI_QUEUE_NAME,
    POST_QUEUE_NAME,
    SOUND_DESIGNER_QUEUE_NAME,
    VIDEO_QUEUE_NAME,
    VOICE_CLONE_QUEUE_NAME,
    queue_health_key,
)

app = FastAPI()
logger = get_logger(name="instagram_reel_creation_fastapi")

load_dotenv(find_dotenv())
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
UPLOAD_FILES_LOCATION = os.getenv("UPLOAD_FILES_LOCATION", "./uploads")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    logger.info("Database initialized")


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.exception(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


VOICE_DESIGN_ROUTE = "/api/v1/voice-design/"
VOICE_DESIGN_PRESETS_ROUTE = "/api/v1/voice-design/presets"


class VoiceDesignLanguage(str, Enum):
    en = "en"
    zh = "zh"
    ar = "ar"
    ur = "ur"


class VoiceDesignPresetName(str, Enum):
    alpha_mentor = "alpha_mentor"
    wise_king = "wise_king"
    borderline_angry_coach = "borderline_angry_coach"
    dark_cinematic_narrator = "dark_cinematic_narrator"


class VoiceDesignGenderPresentation(str, Enum):
    masculine = "masculine"
    feminine = "feminine"
    neutral = "neutral"


class VoiceDesignAgeImpression(str, Enum):
    teen = "teen"
    young = "young"
    mature = "mature"
    elder = "elder"


class VoiceDesignAccentPronunciation(str, Enum):
    neutral_english = "neutral_english"
    american_english = "american_english"
    british_english = "british_english"


class VoiceDesignPitch(str, Enum):
    very_low = "very_low"
    low = "low"
    mid = "mid"
    high = "high"


class VoiceDesignVocalWeight(str, Enum):
    light = "light"
    medium = "medium"
    heavy = "heavy"
    very_heavy = "very_heavy"


class VoiceDesignRoughness(str, Enum):
    smooth = "smooth"
    slight = "slight"
    rough = "rough"
    gritty = "gritty"


class VoiceDesignSpeakingPace(str, Enum):
    very_slow = "very_slow"
    slow = "slow"
    medium = "medium"
    fast = "fast"


class VoiceDesignEnergyLevel(str, Enum):
    calm = "calm"
    controlled = "controlled"
    intense = "intense"
    explosive = "explosive"


class VoiceDesignDramaticPauseIntensity(str, Enum):
    minimal = "minimal"
    natural = "natural"
    strong = "strong"
    cinematic = "cinematic"


class VoiceDesignEmotionalTone(str, Enum):
    serious = "serious"
    inspirational = "inspirational"
    aggressive = "aggressive"


class VoiceDesignAuthorityDominance(str, Enum):
    soft = "soft"
    balanced = "balanced"
    dominant = "dominant"
    commanding = "commanding"


class VoiceDesignWarmthColdness(str, Enum):
    cold = "cold"
    slight_cold = "slight_cold"
    balanced = "balanced"
    warm = "warm"


class VoiceDesignOutputFormat(str, Enum):
    wav = "wav"
    mp3 = "mp3"


class VoiceDesignSampleRate(int, Enum):
    sr_16000 = 16000
    sr_22050 = 22050
    sr_24000 = 24000
    sr_44100 = 44100


class VoiceDesignIdentity(BaseModel):
    gender_presentation: Optional[VoiceDesignGenderPresentation] = None
    age_impression: Optional[VoiceDesignAgeImpression] = None
    accent_pronunciation: Optional[VoiceDesignAccentPronunciation] = None


class VoiceDesignVoiceBody(BaseModel):
    pitch: Optional[VoiceDesignPitch] = None
    vocal_weight: Optional[VoiceDesignVocalWeight] = None
    roughness_grit: Optional[VoiceDesignRoughness] = None


class VoiceDesignDelivery(BaseModel):
    speaking_pace: Optional[VoiceDesignSpeakingPace] = None
    energy_level: Optional[VoiceDesignEnergyLevel] = None
    dramatic_pause_intensity: Optional[VoiceDesignDramaticPauseIntensity] = None


class VoiceDesignPersonality(BaseModel):
    emotional_tone: Optional[List[VoiceDesignEmotionalTone]] = None
    authority_dominance: Optional[VoiceDesignAuthorityDominance] = None
    warmth_coldness: Optional[VoiceDesignWarmthColdness] = None


class VoiceDesignVoiceProfile(BaseModel):
    identity: Optional[VoiceDesignIdentity] = None
    voice_body: Optional[VoiceDesignVoiceBody] = None
    delivery: Optional[VoiceDesignDelivery] = None
    personality: Optional[VoiceDesignPersonality] = None


class VoiceDesignGenerationOptions(BaseModel):
    max_new_tokens: int = Field(2048, ge=1)
    output_format: VoiceDesignOutputFormat = VoiceDesignOutputFormat.wav
    sample_rate: VoiceDesignSampleRate = VoiceDesignSampleRate.sr_24000
    return_base64: bool = False


class VoiceDesignRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    language: VoiceDesignLanguage = VoiceDesignLanguage.en
    preset_name: Optional[VoiceDesignPresetName] = None
    voice_profile: Optional[VoiceDesignVoiceProfile] = None
    generation_options: VoiceDesignGenerationOptions = Field(
        default_factory=VoiceDesignGenerationOptions
    )


class VoiceDesignResponse(BaseModel):
    success: bool
    request_id: str
    derived_instruction: str


VOICE_DESIGN_PRESETS: Dict[str, Dict[str, Any]] = {
    VoiceDesignPresetName.alpha_mentor.value: {
        "identity": {
            "gender_presentation": VoiceDesignGenderPresentation.masculine.value,
            "age_impression": VoiceDesignAgeImpression.mature.value,
            "accent_pronunciation": VoiceDesignAccentPronunciation.neutral_english.value,
        },
        "voice_body": {
            "pitch": VoiceDesignPitch.low.value,
            "vocal_weight": VoiceDesignVocalWeight.heavy.value,
            "roughness_grit": VoiceDesignRoughness.slight.value,
        },
        "delivery": {
            "speaking_pace": VoiceDesignSpeakingPace.slow.value,
            "energy_level": VoiceDesignEnergyLevel.intense.value,
            "dramatic_pause_intensity": VoiceDesignDramaticPauseIntensity.strong.value,
        },
        "personality": {
            "emotional_tone": [
                VoiceDesignEmotionalTone.serious.value,
                VoiceDesignEmotionalTone.inspirational.value,
                VoiceDesignEmotionalTone.aggressive.value,
            ],
            "authority_dominance": VoiceDesignAuthorityDominance.commanding.value,
            "warmth_coldness": VoiceDesignWarmthColdness.balanced.value,
        },
    },
    VoiceDesignPresetName.wise_king.value: {
        "identity": {
            "gender_presentation": VoiceDesignGenderPresentation.masculine.value,
            "age_impression": VoiceDesignAgeImpression.elder.value,
            "accent_pronunciation": VoiceDesignAccentPronunciation.british_english.value,
        },
        "voice_body": {
            "pitch": VoiceDesignPitch.low.value,
            "vocal_weight": VoiceDesignVocalWeight.heavy.value,
            "roughness_grit": VoiceDesignRoughness.smooth.value,
        },
        "delivery": {
            "speaking_pace": VoiceDesignSpeakingPace.slow.value,
            "energy_level": VoiceDesignEnergyLevel.controlled.value,
            "dramatic_pause_intensity": VoiceDesignDramaticPauseIntensity.cinematic.value,
        },
        "personality": {
            "emotional_tone": [
                VoiceDesignEmotionalTone.serious.value,
                VoiceDesignEmotionalTone.inspirational.value,
            ],
            "authority_dominance": VoiceDesignAuthorityDominance.dominant.value,
            "warmth_coldness": VoiceDesignWarmthColdness.warm.value,
        },
    },
    VoiceDesignPresetName.borderline_angry_coach.value: {
        "identity": {
            "gender_presentation": VoiceDesignGenderPresentation.masculine.value,
            "age_impression": VoiceDesignAgeImpression.mature.value,
            "accent_pronunciation": VoiceDesignAccentPronunciation.american_english.value,
        },
        "voice_body": {
            "pitch": VoiceDesignPitch.low.value,
            "vocal_weight": VoiceDesignVocalWeight.heavy.value,
            "roughness_grit": VoiceDesignRoughness.rough.value,
        },
        "delivery": {
            "speaking_pace": VoiceDesignSpeakingPace.medium.value,
            "energy_level": VoiceDesignEnergyLevel.intense.value,
            "dramatic_pause_intensity": VoiceDesignDramaticPauseIntensity.strong.value,
        },
        "personality": {
            "emotional_tone": [
                VoiceDesignEmotionalTone.inspirational.value,
                VoiceDesignEmotionalTone.aggressive.value,
            ],
            "authority_dominance": VoiceDesignAuthorityDominance.commanding.value,
            "warmth_coldness": VoiceDesignWarmthColdness.slight_cold.value,
        },
    },
    VoiceDesignPresetName.dark_cinematic_narrator.value: {
        "identity": {
            "gender_presentation": VoiceDesignGenderPresentation.masculine.value,
            "age_impression": VoiceDesignAgeImpression.mature.value,
            "accent_pronunciation": VoiceDesignAccentPronunciation.neutral_english.value,
        },
        "voice_body": {
            "pitch": VoiceDesignPitch.very_low.value,
            "vocal_weight": VoiceDesignVocalWeight.heavy.value,
            "roughness_grit": VoiceDesignRoughness.gritty.value,
        },
        "delivery": {
            "speaking_pace": VoiceDesignSpeakingPace.very_slow.value,
            "energy_level": VoiceDesignEnergyLevel.controlled.value,
            "dramatic_pause_intensity": VoiceDesignDramaticPauseIntensity.cinematic.value,
        },
        "personality": {
            "emotional_tone": [
                VoiceDesignEmotionalTone.serious.value,
                VoiceDesignEmotionalTone.aggressive.value,
            ],
            "authority_dominance": VoiceDesignAuthorityDominance.dominant.value,
            "warmth_coldness": VoiceDesignWarmthColdness.cold.value,
        },
    },
}


def _voice_design_json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {
            key: _voice_design_json_safe(inner_value)
            for key, inner_value in value.items()
        }
    if isinstance(value, list):
        return [_voice_design_json_safe(inner_value) for inner_value in value]
    return value


def _voice_design_model_dump(model: BaseModel) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return _voice_design_json_safe(
            model.model_dump(exclude_none=True)  # type: ignore[attr-defined]
        )
    return _voice_design_json_safe(model.dict(exclude_none=True))


def _voice_design_deep_merge(
    base: Dict[str, Any], override: Dict[str, Any]
) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if (
            isinstance(value, dict)
            and isinstance(merged.get(key), dict)
        ):
            merged[key] = _voice_design_deep_merge(merged[key], value)
            continue
        merged[key] = value
    return merged


def _resolve_voice_design_profile(
    payload: VoiceDesignRequest,
) -> Optional[VoiceDesignVoiceProfile]:
    preset_data: Dict[str, Any] = {}
    if payload.preset_name is not None:
        preset_data = VOICE_DESIGN_PRESETS.get(payload.preset_name.value, {})

    custom_data: Dict[str, Any] = {}
    if payload.voice_profile is not None:
        custom_data = _voice_design_model_dump(payload.voice_profile)

    merged_profile = _voice_design_deep_merge(preset_data, custom_data)
    if not merged_profile:
        return None
    return VoiceDesignVoiceProfile(**merged_profile)


def _voice_design_invalid_parameter_content(
    field: str,
    message: str,
    received: Any = None,
    allowed_values: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    details: Dict[str, Any] = {"field": field}
    if received is not None:
        details["received"] = received
    if allowed_values:
        details["allowed_values"] = allowed_values
    return {
        "success": False,
        "error": {
            "code": "INVALID_PARAMETER",
            "message": message,
            "details": details,
        },
    }


def _voice_design_request_payload(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, BaseModel):
        return _voice_design_model_dump(payload)
    if isinstance(payload, dict):
        return _voice_design_json_safe(payload)
    if payload is None:
        return {}
    return {"raw_payload": _voice_design_json_safe(payload)}


def _record_sound_design_prompt(
    *,
    prompt_status: SoundDesignPromptStatus,
    request_payload: Any,
    response_payload: Dict[str, Any],
    request_id: Optional[str] = None,
    derived_instruction: Optional[str] = None,
    error_code: Optional[str] = None,
    error_message: Optional[str] = None,
) -> None:
    payload_doc = _voice_design_request_payload(request_payload)
    now = datetime.utcnow()
    language = payload_doc.get("language")
    preset_name = payload_doc.get("preset_name")
    text = str(payload_doc.get("text") or "")
    doc = SoundDesignPromptModel(
        sound_design_id=uuid4().hex,
        status=prompt_status,
        request_payload=payload_doc,
        response_payload=_voice_design_json_safe(response_payload),
        text=text,
        custom_voice_text=text,
        language=None if language is None else str(language),
        preset_name=None if preset_name is None else str(preset_name),
        request_id=request_id,
        derived_instruction=derived_instruction,
        error_code=error_code,
        error_message=error_message,
        created_at=now,
        updated_at=now,
    ).to_bson()

    try:
        db = get_db()
        db[SOUND_DESIGN_PROMPT_COLLECTION].insert_one(doc)
    except Exception:
        logger.exception(
            "Failed to store sound design prompt log sound_design_id=%s",
            doc["sound_design_id"],
        )


def _voice_design_error_allowed_values(error: Dict[str, Any]) -> Optional[List[Any]]:
    ctx = error.get("ctx") or {}
    enum_values = ctx.get("enum_values")
    if enum_values:
        return [
            value.value if hasattr(value, "value") else value
            for value in enum_values
        ]
    expected = ctx.get("expected")
    if isinstance(expected, str):
        raw_parts = expected.replace(" or ", ", ").split(",")
        parsed: List[Any] = []
        for raw_value in raw_parts:
            value = raw_value.strip().strip("'").strip('"')
            if not value:
                continue
            if value.isdigit():
                parsed.append(int(value))
                continue
            parsed.append(value)
        if parsed:
            return parsed
    return None


def _voice_design_error_field(loc: Tuple[Any, ...]) -> str:
    fields: List[str] = []
    for raw_part in loc:
        if raw_part == "body":
            continue
        if raw_part == "voice_profile":
            continue
        fields.append(str(raw_part))
    if not fields:
        return "body"
    return ".".join(fields)


def _voice_design_error_received(
    body: Any, loc: Tuple[Any, ...], fallback: Any
) -> Any:
    if fallback is not None:
        return fallback
    if body is None:
        return None

    current = body
    for raw_part in loc:
        if raw_part == "body":
            continue

        if isinstance(current, dict):
            if raw_part not in current:
                return None
            current = current[raw_part]
            continue

        if isinstance(current, list) and isinstance(raw_part, int):
            if raw_part < 0 or raw_part >= len(current):
                return None
            current = current[raw_part]
            continue

        return None
    return current


@app.exception_handler(RequestValidationError)
async def request_validation_exception(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    if not request.url.path.startswith(VOICE_DESIGN_ROUTE.rstrip("/")):
        return await request_validation_exception_handler(request, exc)

    request_payload = _voice_design_request_payload(getattr(exc, "body", None))
    errors = exc.errors()
    if not errors:
        content = _voice_design_invalid_parameter_content(
            field="body",
            message="Invalid request body",
        )
        _record_sound_design_prompt(
            prompt_status="failed",
            request_payload=request_payload,
            response_payload=content,
            error_code="INVALID_PARAMETER",
            error_message="Invalid request body",
        )
        return JSONResponse(status_code=400, content=content)

    primary_error = errors[0]
    loc = tuple(primary_error.get("loc", ()))
    field = _voice_design_error_field(loc)
    error_type = str(primary_error.get("type", ""))
    message = f"Invalid value for {field}"
    if "missing" in error_type:
        message = f"Missing required field {field}"

    received = _voice_design_error_received(
        getattr(exc, "body", None),
        loc,
        primary_error.get("input"),
    )
    allowed_values = _voice_design_error_allowed_values(primary_error)
    content = _voice_design_invalid_parameter_content(
        field=field,
        message=message,
        received=received,
        allowed_values=allowed_values,
    )
    _record_sound_design_prompt(
        prompt_status="failed",
        request_payload=request_payload,
        response_payload=content,
        error_code="INVALID_PARAMETER",
        error_message=message,
    )
    return JSONResponse(status_code=400, content=content)


def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


def _serialize_raw_post(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc = dict(doc)
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


def _serialize_with_id(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc = dict(doc)
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


def _parse_object_id(raw_id: str) -> ObjectId:
    try:
        return ObjectId(raw_id)
    except (InvalidId, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid _id") from exc


class CallApiRequest(BaseModel):
    ai_type: str = Field(..., min_length=1)
    input: Dict[str, Any] = Field(default_factory=dict)


class CallApiResponse(BaseModel):
    message: str
    ai_type: str
    job_id: str
    status: str


class VoiceCloneEnqueueRequest(BaseModel):
    ref_audio_path: str = Field(..., min_length=1)
    ref_text: str = Field(..., min_length=1)


class VoiceCloneEnqueueResponse(BaseModel):
    message: str
    voice_clone_job_id: str
    status: str


class CustomVoiceDesignEnqueueRequest(BaseModel):
    request_id: str = Field(..., min_length=1)


class CustomVoiceStatusResponse(BaseModel):
    request_id: str
    status: str
    custom_voice_available: bool
    error_code: Optional[str] = None
    error_message: Optional[str] = None


def _parse_hms(value: str) -> int:
    parts = value.split(":")
    if len(parts) != 3:
        raise HTTPException(status_code=400, detail="Invalid time format")
    hours, minutes, seconds = parts
    try:
        h = int(hours)
        m = int(minutes)
        s = int(seconds)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid time format") from exc
    if h < 0 or m < 0 or s < 0 or m > 59 or s > 59:
        raise HTTPException(status_code=400, detail="Invalid time format")
    return h * 3600 + m * 60 + s


def _format_hms(total_seconds: float) -> str:
    total = int(total_seconds)
    hours = total // 3600
    minutes = (total % 3600) // 60
    seconds = total % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _probe_duration_seconds(file_location: str) -> float:
    path = Path(file_location)
    if not path.exists():
        raise HTTPException(status_code=400, detail="file_location not found")
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise HTTPException(status_code=400, detail="Unable to read media duration")
    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid media duration") from exc


def _validate_times(start_time: str, end_time: str, duration_seconds: float) -> None:
    start_seconds = _parse_hms(start_time)
    end_seconds = _parse_hms(end_time)
    if start_seconds < 0:
        raise HTTPException(status_code=400, detail="start_time must be >= 00:00:00")
    if end_seconds > int(duration_seconds):
        raise HTTPException(status_code=400, detail="end_time exceeds file duration")
    if end_seconds <= start_seconds:
        raise HTTPException(status_code=400, detail="end_time must be > start_time")


async def _require_worker_health(
    redis: Any, queue_name: str, worker_label: str
) -> None:
    health_key = queue_health_key(queue_name)
    health_data = await redis.get(health_key)
    if health_data:
        return
    logger.error(
        "%s worker is unavailable. Missing health key=%s queue=%s",
        worker_label,
        health_key,
        queue_name,
    )
    raise HTTPException(
        status_code=503,
        detail=f"{worker_label} worker unavailable",
    )


@app.get(VOICE_DESIGN_PRESETS_ROUTE)
def list_voice_design_presets() -> Dict[str, Any]:
    return SoundPromptPreset.get_presets()


@app.get(f"{VOICE_DESIGN_PRESETS_ROUTE}/{{preset_id}}")
def get_voice_design_preset(preset_id: str) -> Any:
    response = SoundPromptPreset.get_preset_value(preset_id)
    if response.get("success"):
        return response
    return JSONResponse(status_code=404, content=response)


@app.post(VOICE_DESIGN_ROUTE, response_model=VoiceDesignResponse)
def create_voice_design(payload: VoiceDesignRequest) -> Any:
    request_payload = _voice_design_model_dump(payload)

    try:
        profile = _resolve_voice_design_profile(payload)
        if profile is None:
            message = "Either preset_name or voice_profile is required"
            content = _voice_design_invalid_parameter_content(
                field="voice_profile",
                message=message,
            )
            _record_sound_design_prompt(
                prompt_status="failed",
                request_payload=request_payload,
                response_payload=content,
                error_code="INVALID_PARAMETER",
                error_message=message,
            )
            return JSONResponse(status_code=400, content=content)

        profile_data = _voice_design_model_dump(profile)
        try:
            resolved_profile = SoundPromptVoiceProfile(**profile_data)
        except ValidationError as exc:
            errors = exc.errors()
            primary_error = errors[0] if errors else {}
            loc = tuple(primary_error.get("loc", ()))
            field = "voice_profile"
            if loc:
                field = f"voice_profile.{'.'.join(str(part) for part in loc)}"
            message = (
                "Resolved voice_profile is incomplete. "
                "Provide a complete profile or use a complete preset."
            )
            content = _voice_design_invalid_parameter_content(
                field=field,
                message=message,
                received=profile_data,
                allowed_values=_voice_design_error_allowed_values(primary_error),
            )
            _record_sound_design_prompt(
                prompt_status="failed",
                request_payload=request_payload,
                response_payload=content,
                error_code="INVALID_PARAMETER",
                error_message=message,
            )
            return JSONResponse(status_code=400, content=content)

        derived_instruction = SoundPromptCreator.build_voice_instruction(resolved_profile)
        request_id = str(uuid4())
        response_payload = {
            "success": True,
            "request_id": request_id,
            "derived_instruction": derived_instruction,
        }
        _record_sound_design_prompt(
            prompt_status="passed",
            request_payload=request_payload,
            response_payload=response_payload,
            request_id=request_id,
            derived_instruction=derived_instruction,
        )

        logger.info(
            "Voice design generated request_id=%s language=%s preset=%s",
            request_id,
            payload.language.value,
            payload.preset_name.value if payload.preset_name is not None else None,
        )
        return response_payload
    except Exception as exc:
        failure_content = {
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Internal server error",
            },
        }
        _record_sound_design_prompt(
            prompt_status="failed",
            request_payload=request_payload,
            response_payload=failure_content,
            error_code="INTERNAL_SERVER_ERROR",
            error_message=str(exc),
        )
        raise


@app.post("/enqueue/custom_voice_design")
async def enqueue_custom_voice_design(
    payload: CustomVoiceDesignEnqueueRequest,
) -> JSONResponse:
    request_id = payload.request_id.strip()
    if not request_id:
        raise HTTPException(status_code=400, detail="request_id is required")

    db = get_db()
    prompt_doc = db[SOUND_DESIGN_PROMPT_COLLECTION].find_one(
        {"request_id": request_id},
        {"_id": 0, "status": 1},
    )
    if prompt_doc is None:
        raise HTTPException(status_code=404, detail="request_id not found")

    if prompt_doc.get("status") != "passed":
        raise HTTPException(
            status_code=409,
            detail="voice design is not in passed state",
        )

    try:
        redis = await create_pool(RedisSettings.from_dsn(REDIS_URL))
    except Exception as exc:
        logger.error("Unable to connect to Redis: %s", exc)
        raise HTTPException(status_code=503, detail="redis unavailable") from exc

    try:
        await _require_worker_health(
            redis,
            SOUND_DESIGNER_QUEUE_NAME,
            "sound designer",
        )
        job = await redis.enqueue_job(
            "process_sound_design",
            request_id,
            _queue_name=SOUND_DESIGNER_QUEUE_NAME,
        )
    finally:
        await redis.close()

    if job is None:
        raise HTTPException(status_code=500, detail="enqueue failed")

    logger.info(
        "Enqueued sound designer job request_id=%s as arq job %s",
        request_id,
        job.job_id,
    )
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "message": "custom voice design job queued",
            "request_id": request_id,
            "job_id": job.job_id,
            "status": "queued",
        },
    )


@app.post("/uploads")
def upload_video_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="file is required")
    if file.content_type and not (
        file.content_type.startswith("video/")
        or file.content_type.startswith("audio/")
    ):
        raise HTTPException(
            status_code=400,
            detail="only video or audio uploads are supported",
        )

    upload_dir = Path(UPLOAD_FILES_LOCATION)
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename).suffix
    stored_name = f"{uuid4().hex}{ext}"
    destination = upload_dir / stored_name

    try:
        with destination.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    return {
        "file_name": file.filename,
        "stored_name": stored_name,
        "file_location": str(destination.resolve()),
    }


@app.post("/videos", response_model=VideoSchema)
def create_video(payload: VideoCreate) -> Dict[str, Any]:
    db = get_db()
    now = datetime.utcnow()
    video_id = uuid4().hex

    doc = {
        "video_id": video_id,
        "video_title": payload.video_title,
        "video_size": payload.video_size,
        "video_introduction": payload.video_introduction,
        "creation_time": now,
        "modification_time": now,
        "active": True if payload.active is None else payload.active,
        "video_tags": payload.video_tags or [],
        "status": "created",
        "output_file_location": None,
        "job_id": None,
        "error_reason": None,
    }

    try:
        db.videos.insert_one(doc)
    except DuplicateKeyError as exc:
        logger.error("Duplicate video_id on insert: %s", exc)
        raise HTTPException(status_code=409, detail="video_id already exists") from exc

    logger.info("Created video %s", video_id)
    return _serialize(doc)


@app.get("/videos", response_model=List[VideoSchema])
def list_videos() -> List[Dict[str, Any]]:
    try:
        db = get_db()
        docs = [_serialize(doc) for doc in db.videos.find({})]
        logger.info(f"Documents length: {len(docs)}\n{docs}")
        return docs
    except Exception as exc:
        logger.exception("Failed to list videos")
        raise HTTPException(status_code=500, detail="Unable to list videos") from exc


@app.get("/videos/{video_id}", response_model=VideoSchema)
def get_video(video_id: str) -> Dict[str, Any]:
    db = get_db()
    doc = db.videos.find_one({"video_id": video_id})
    if doc is None:
        raise HTTPException(status_code=404, detail="video not found")
    return _serialize(doc)


@app.patch("/videos/{video_id}", response_model=VideoSchema)
def update_video(video_id: str, payload: VideoUpdate) -> Dict[str, Any]:
    db = get_db()
    update = payload.dict(exclude_unset=True)
    update["modification_time"] = datetime.utcnow()

    doc = db.videos.find_one_and_update(
        {"video_id": video_id},
        {"$set": update},
        return_document=ReturnDocument.AFTER,
    )

    if doc is None:
        raise HTTPException(status_code=404, detail="video not found")

    logger.info("Updated video %s", video_id)
    return _serialize(doc)


@app.delete("/videos/{video_id}", response_model=VideoSchema)
def delete_video(video_id: str) -> Dict[str, Any]:
    db = get_db()
    doc = db.videos.find_one_and_delete({"video_id": video_id})
    if doc is None:
        raise HTTPException(status_code=404, detail="video not found")

    parts = list(
        db.video_parts.find({"video_id": video_id}, {"file_location": 1})
    )
    db.video_parts.delete_many({"video_id": video_id})

    file_locations = [doc.get("output_file_location")] + [
        part.get("file_location") for part in parts
    ]
    for file_location in file_locations:
        if not file_location:
            continue
        try:
            path = Path(file_location)
            if path.exists():
                path.unlink()
        except Exception as exc:
            logger.warning("Failed to delete file %s: %s", file_location, exc)

    logger.info("Deleted video %s", video_id)
    return _serialize(doc)


@app.post("/videos/{video_id}/enqueue")
async def enqueue_video(video_id: str) -> JSONResponse:
    db = get_db()
    video = db.videos.find_one({"video_id": video_id})
    if video is None:
        raise HTTPException(status_code=404, detail="video not found")

    try:
        redis = await create_pool(RedisSettings.from_dsn(REDIS_URL))
    except Exception as exc:
        logger.error("Unable to connect to Redis: %s", exc)
        raise HTTPException(status_code=503, detail="redis unavailable") from exc

    try:
        await _require_worker_health(
            redis,
            VIDEO_QUEUE_NAME,
            "video",
        )
        job = await redis.enqueue_job(
            "process_video",
            video_id,
            _queue_name=VIDEO_QUEUE_NAME,
        )
    finally:
        await redis.close()

    if job is None:
        raise HTTPException(status_code=500, detail="enqueue failed")

    try:
        db.videos.update_one(
            {"video_id": video_id},
            {
                "$set": {
                    "status": "queued",
                    "job_id": job.job_id,
                    "error_reason": None,
                    "modification_time": datetime.utcnow(),
                }
            },
        )
    except Exception as exc:
        logger.error("Failed to update video enqueue status: %s", exc)
        raise HTTPException(status_code=500, detail="enqueue status update failed") from exc

    logger.info("Enqueued video %s as job %s", video_id, job.job_id)
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "message": "video queued",
            "video_id": video_id,
            "job_id": job.job_id,
            "status": "queued",
        },
    )


@app.post("/enque_posts")
async def enqueue_posts() -> JSONResponse:
    try:
        redis = await create_pool(RedisSettings.from_dsn(REDIS_URL))
    except Exception as exc:
        logger.error("Unable to connect to Redis: %s", exc)
        raise HTTPException(status_code=503, detail="redis unavailable") from exc

    try:
        await _require_worker_health(
            redis,
            POST_QUEUE_NAME,
            "post",
        )
        job = await redis.enqueue_job(
            "process_posts",
            _queue_name=POST_QUEUE_NAME,
        )
    finally:
        await redis.close()

    if job is None:
        raise HTTPException(status_code=500, detail="enqueue failed")

    logger.info("Enqueued post worker as job %s", job.job_id)
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "message": "post worker queued",
            "job_id": job.job_id,
            "status": "queued",
        },
    )


@app.post("/voice-clones/enqueue", response_model=VoiceCloneEnqueueResponse)
async def enqueue_voice_clone(payload: VoiceCloneEnqueueRequest) -> JSONResponse:
    db = get_db()
    now = datetime.utcnow()
    voice_clone_job_id = uuid4().hex

    ref_audio_path = payload.ref_audio_path.strip()
    ref_text = payload.ref_text.strip()
    if not ref_audio_path:
        raise HTTPException(status_code=400, detail="ref_audio_path is required")
    if not ref_text:
        raise HTTPException(status_code=400, detail="ref_text is required")

    path = Path(ref_audio_path)
    if not path.exists():
        raise HTTPException(status_code=400, detail="ref_audio_path not found")
    if path.suffix.lower() != ".wav":
        raise HTTPException(status_code=400, detail="ref_audio_path must be a .wav file")

    doc = VoiceCloneJobModel(
        job_id=voice_clone_job_id,
        ref_audio_path=ref_audio_path,
        ref_text=ref_text,
        status="queued",
        progress=0.0,
        result_path=None,
        error_reason=None,
        created_at=now,
        started_at=None,
        completed_at=None,
        updated_at=now,
    ).to_bson()

    try:
        db[VOICE_CLONE_JOB_COLLECTION].insert_one(doc)
    except DuplicateKeyError as exc:
        logger.error("Duplicate job_id on voice clone insert: %s", exc)
        raise HTTPException(status_code=409, detail="job_id already exists") from exc

    try:
        redis = await create_pool(RedisSettings.from_dsn(REDIS_URL))
    except Exception as exc:
        db[VOICE_CLONE_JOB_COLLECTION].update_one(
            {"job_id": voice_clone_job_id},
            {
                "$set": {
                    "status": "failed",
                    "error_reason": "redis unavailable",
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        logger.error("Unable to connect to Redis: %s", exc)
        raise HTTPException(status_code=503, detail="redis unavailable") from exc

    try:
        await _require_worker_health(
            redis,
            VOICE_CLONE_QUEUE_NAME,
            "voice clone",
        )
        job = await redis.enqueue_job(
            "process_voice_clone_job",
            voice_clone_job_id,
            _queue_name=VOICE_CLONE_QUEUE_NAME,
        )
    except HTTPException:
        db[VOICE_CLONE_JOB_COLLECTION].update_one(
            {"job_id": voice_clone_job_id},
            {
                "$set": {
                    "status": "failed",
                    "error_reason": "voice clone worker unavailable",
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        raise
    except Exception as exc:
        db[VOICE_CLONE_JOB_COLLECTION].update_one(
            {"job_id": voice_clone_job_id},
            {
                "$set": {
                    "status": "failed",
                    "error_reason": "enqueue failed",
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        logger.error("Failed to enqueue voice clone job: %s", exc)
        raise HTTPException(status_code=500, detail="enqueue failed") from exc
    finally:
        await redis.close()

    if job is None:
        db[VOICE_CLONE_JOB_COLLECTION].update_one(
            {"job_id": voice_clone_job_id},
            {
                "$set": {
                    "status": "failed",
                    "error_reason": "enqueue failed",
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        raise HTTPException(status_code=500, detail="enqueue failed")

    logger.info(
        "Enqueued voice clone job %s as arq job %s",
        voice_clone_job_id,
        job.job_id,
    )
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "message": "voice clone job queued",
            "voice_clone_job_id": voice_clone_job_id,
            "status": "queued",
        },
    )


@app.get("/voice-clones")
def list_voice_clones(
    response: Response, page: int = 1, page_size: int = 10
) -> List[Dict[str, Any]]:
    if page < 1 or page_size < 1:
        raise HTTPException(
            status_code=400, detail="page and page_size must be >= 1"
        )

    db = get_db()
    total_count = db[VOICE_CLONE_JOB_COLLECTION].count_documents({})
    response.headers["X-Total-Count"] = str(total_count)
    skip = (page - 1) * page_size
    cursor = (
        db[VOICE_CLONE_JOB_COLLECTION]
        .find({}, {"_id": 0})
        .sort("updated_at", -1)
        .skip(skip)
        .limit(page_size)
    )
    return [dict(doc) for doc in cursor]


@app.get("/voice-clones/{voice_clone_job_id}")
def get_voice_clone(voice_clone_job_id: str) -> Dict[str, Any]:
    db = get_db()
    doc = db[VOICE_CLONE_JOB_COLLECTION].find_one(
        {"job_id": voice_clone_job_id},
        {"_id": 0},
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="voice clone job not found")
    return dict(doc)


@app.get("/voice-clones/{voice_clone_job_id}/download")
def download_voice_clone(voice_clone_job_id: str) -> FileResponse:
    db = get_db()
    doc = db[VOICE_CLONE_JOB_COLLECTION].find_one(
        {"job_id": voice_clone_job_id},
        {"_id": 0},
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="voice clone job not found")
    if doc.get("status") != "completed":
        raise HTTPException(status_code=409, detail="voice clone is not completed yet")

    result_path = str(doc.get("result_path") or "").strip()
    if not result_path:
        raise HTTPException(status_code=404, detail="output file not available")

    output_path = Path(result_path)
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="output file not found")

    return FileResponse(
        path=output_path,
        media_type="audio/wav",
        filename=f"{voice_clone_job_id}.wav",
    )


@app.get("/custom-voices")
def list_custom_voices() -> List[Dict[str, Any]]:
    db = get_db()
    cursor = (
        db[CUSTOM_VOICES_COLLECTION]
        .find({}, {"_id": 0})
        .sort("updated_at", -1)
    )
    return [dict(doc) for doc in cursor]


@app.get("/custom-voices/status/{request_id}", response_model=CustomVoiceStatusResponse)
def get_custom_voice_status(request_id: str) -> Dict[str, Any]:
    normalized_request_id = request_id.strip()
    if not normalized_request_id:
        raise HTTPException(status_code=400, detail="request_id is required")

    db = get_db()
    voice_doc = db[CUSTOM_VOICES_COLLECTION].find_one(
        {"request_id": normalized_request_id},
        {"_id": 0, "request_id": 1},
    )
    if voice_doc is not None:
        return {
            "request_id": normalized_request_id,
            "status": "completed",
            "custom_voice_available": True,
            "error_code": None,
            "error_message": None,
        }

    prompt_doc = db[SOUND_DESIGN_PROMPT_COLLECTION].find_one(
        {"request_id": normalized_request_id},
        {"_id": 0, "status": 1, "error_code": 1, "error_message": 1},
        sort=[("updated_at", -1)],
    )
    if prompt_doc is None:
        return {
            "request_id": normalized_request_id,
            "status": "not_found",
            "custom_voice_available": False,
            "error_code": "REQUEST_NOT_FOUND",
            "error_message": "request_id not found",
        }

    prompt_status = str(prompt_doc.get("status") or "").strip().lower()
    if prompt_status == "failed":
        return {
            "request_id": normalized_request_id,
            "status": "failed",
            "custom_voice_available": False,
            "error_code": prompt_doc.get("error_code"),
            "error_message": prompt_doc.get("error_message"),
        }

    return {
        "request_id": normalized_request_id,
        "status": "in_progress",
        "custom_voice_available": False,
        "error_code": None,
        "error_message": None,
    }


@app.get("/custom-voices/{request_id}")
def get_custom_voice(request_id: str) -> Dict[str, Any]:
    normalized_request_id = request_id.strip()
    if not normalized_request_id:
        raise HTTPException(status_code=400, detail="request_id is required")

    db = get_db()
    voice_doc = db[CUSTOM_VOICES_COLLECTION].find_one(
        {"request_id": normalized_request_id},
        {"_id": 0},
    )
    if voice_doc is None:
        raise HTTPException(status_code=404, detail="custom voice not found")

    prompt_doc = db[SOUND_DESIGN_PROMPT_COLLECTION].find_one(
        {"request_id": normalized_request_id},
        {"_id": 0},
        sort=[("updated_at", -1)],
    )

    return {
        "custom_voice": dict(voice_doc),
        "sound_design_prompt": dict(prompt_doc) if prompt_doc is not None else None,
    }


@app.get("/custom-voices/{request_id}/audio")
def stream_custom_voice_audio(request_id: str) -> FileResponse:
    normalized_request_id = request_id.strip()
    if not normalized_request_id:
        raise HTTPException(status_code=400, detail="request_id is required")

    db = get_db()
    voice_doc = db[CUSTOM_VOICES_COLLECTION].find_one(
        {"request_id": normalized_request_id},
        {"_id": 0, "output_file_location": 1},
    )
    if voice_doc is None:
        raise HTTPException(status_code=404, detail="custom voice not found")

    output_file_location = str(voice_doc.get("output_file_location") or "").strip()
    if not output_file_location:
        raise HTTPException(status_code=404, detail="output file not available")

    output_path = Path(output_file_location)
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="output file not found")

    media_type = "audio/mpeg" if output_path.suffix.lower() == ".mp3" else "audio/wav"
    return FileResponse(
        path=output_path,
        media_type=media_type,
        filename=output_path.name,
    )


@app.post("/video-parts", response_model=VideoPartSchema)
def create_video_part(payload: VideoPartCreate) -> Dict[str, Any]:
    db = get_db()
    now = datetime.utcnow()
    duration_seconds = _probe_duration_seconds(payload.file_location)
    _validate_times(payload.start_time, payload.end_time, duration_seconds)
    file_duration = _format_hms(duration_seconds)
    video_parts_id = payload.video_parts_id or uuid4().hex

    doc = {
        "video_parts_id": video_parts_id,
        "video_id": payload.video_id,
        "file_part_name": payload.file_part_name,
        "part_number": payload.part_number,
        "file_location": payload.file_location,
        "file_duration": file_duration,
        "start_time": payload.start_time,
        "end_time": payload.end_time,
        "video_size": file_duration,
        "total_duration": duration_seconds,
        "selected_duration": payload.selected_duration,
        "modification_time": now,
        "active": True if payload.active is None else payload.active,
        "creation_time": now,
    }

    db.video_parts.insert_one(doc)
    logger.info("Created video part %s", payload.video_parts_id)
    return _serialize(doc)


@app.get("/video-parts", response_model=List[VideoPartSchema])
def list_video_parts() -> List[Dict[str, Any]]:
    db = get_db()
    docs = [_serialize(doc) for doc in db.video_parts.find({})]
    return docs


@app.get("/video-parts/{video_parts_id}", response_model=VideoPartSchema)
def get_video_part(video_parts_id: int) -> Dict[str, Any]:
    db = get_db()
    doc = db.video_parts.find_one({"video_parts_id": video_parts_id})
    if doc is None:
        raise HTTPException(status_code=404, detail="video part not found")
    return _serialize(doc)


@app.patch("/video-parts/{video_parts_id}", response_model=VideoPartSchema)
def update_video_part(
    video_parts_id: int, payload: VideoPartUpdate
) -> Dict[str, Any]:
    db = get_db()
    existing = db.video_parts.find_one({"video_parts_id": video_parts_id})
    if existing is None:
        raise HTTPException(status_code=404, detail="video part not found")
    update = payload.dict(exclude_unset=True)
    merged = {**existing, **update}
    duration_seconds = _probe_duration_seconds(merged.get("file_location", ""))
    _validate_times(merged.get("start_time", ""), merged.get("end_time", ""), duration_seconds)
    update["file_duration"] = _format_hms(duration_seconds)
    update["video_size"] = _format_hms(duration_seconds)
    update["total_duration"] = duration_seconds
    update["modification_time"] = datetime.utcnow()

    doc = db.video_parts.find_one_and_update(
        {"video_parts_id": video_parts_id},
        {"$set": update},
        return_document=ReturnDocument.AFTER,
    )

    logger.info("Updated video part %s", video_parts_id)
    return _serialize(doc)


@app.delete("/video-parts/{video_parts_id}", response_model=VideoPartSchema)
def delete_video_part(video_parts_id: int) -> Dict[str, Any]:
    db = get_db()
    doc = db.video_parts.find_one_and_delete({"video_parts_id": video_parts_id})
    if doc is None:
        raise HTTPException(status_code=404, detail="video part not found")

    logger.info("Deleted video part %s", video_parts_id)
    return _serialize(doc)


@app.post("/call_api", response_model=CallApiResponse)
async def call_api(payload: CallApiRequest) -> JSONResponse:
    ai_type = payload.ai_type
    if ai_type not in AI_TYPE_PROMPT_MAP:
        allowed = ", ".join(AI_TYPES)
        raise HTTPException(
            status_code=400, detail=f"Invalid ai_type. Allowed: {allowed}"
        )

    required_fields = AI_TYPE_REQUIRED_FIELDS.get(ai_type, [])
    missing = [
        field
        for field in required_fields
        if field not in payload.input or str(payload.input[field]).strip() == ""
    ]
    if missing:
        missing_list = ", ".join(missing)
        raise HTTPException(
            status_code=400,
            detail=f"Missing required input fields for {ai_type}: {missing_list}",
        )

    try:
        redis = await create_pool(RedisSettings.from_dsn(REDIS_URL))
    except Exception as exc:
        logger.error("Unable to connect to Redis: %s", exc)
        raise HTTPException(status_code=503, detail="redis unavailable") from exc

    try:
        await _require_worker_health(
            redis,
            AI_QUEUE_NAME,
            "ai",
        )
        job = await redis.enqueue_job(
            "process_ai_task",
            ai_type,
            payload.input,
            _queue_name=AI_QUEUE_NAME,
        )
    finally:
        await redis.close()

    if job is None:
        raise HTTPException(status_code=500, detail="enqueue failed")

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "message": "ai job queued",
            "ai_type": ai_type,
            "job_id": job.job_id,
            "status": "queued",
        },
    )


@app.post("/monthly-figures", response_model=RawPostsDataResponse)
def create_monthly_figures(payload: RawPostsDataCreate) -> Dict[str, Any]:
    db = get_db()
    model = RawPostsDataModel(
        code=payload.code,
        name=payload.name,
        country=payload.country,
        dob=payload.dob,
        excellence_field=payload.excellence_field,
        challenges_faced=payload.challenges_faced,
        quote_created=payload.quote_created if payload.quote_created is not None else False,
        posted=payload.posted if payload.posted is not None else False,
        quote_created_on=payload.quote_created_on,
        posted_on=payload.posted_on,
    )
    doc = model.to_bson()

    try:
        result = db[RAW_POSTS_COLLECTION].insert_one(doc)
    except DuplicateKeyError as exc:
        logger.error("Duplicate code on raw_posts_data insert: %s", exc)
        raise HTTPException(status_code=409, detail="code already exists") from exc

    doc["_id"] = result.inserted_id
    return _serialize_raw_post(doc)


@app.get("/monthly-figures", response_model=List[RawPostsDataResponse])
def list_monthly_figures(
    response: Response, page: int = 1, page_size: int = 20
) -> List[Dict[str, Any]]:
    if page < 1 or page_size < 1:
        raise HTTPException(
            status_code=400, detail="page and page_size must be >= 1"
        )

    db = get_db()
    total_count = db[RAW_POSTS_COLLECTION].count_documents({})
    response.headers["X-Total-Count"] = str(total_count)
    skip = (page - 1) * page_size
    cursor = db[RAW_POSTS_COLLECTION].find({}).skip(skip).limit(page_size)
    return [_serialize_raw_post(doc) for doc in cursor]


@app.get("/raw_posts", response_model=List[RawPostsDataResponse])
def list_raw_posts(
    response: Response,
    page: int = 1,
    page_size: int = 20,
    quote_created: Optional[bool] = None,
    posted: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    if page < 1 or page_size < 1:
        raise HTTPException(
            status_code=400, detail="page and page_size must be >= 1"
        )

    db = get_db()
    skip = (page - 1) * page_size
    query: Dict[str, Any] = {}
    if quote_created is not None:
        query["quote_created"] = quote_created
    if posted is not None:
        query["posted"] = posted

    total_count = db[RAW_POSTS_COLLECTION].count_documents(query)
    response.headers["X-Total-Count"] = str(total_count)
    cursor = db[RAW_POSTS_COLLECTION].find(query).skip(skip).limit(page_size)
    return [_serialize_raw_post(doc) for doc in cursor]


@app.get("/monthly-figures/{item_id}", response_model=RawPostsDataResponse)
def get_monthly_figure(item_id: str) -> Dict[str, Any]:
    db = get_db()
    oid = _parse_object_id(item_id)
    doc = db[RAW_POSTS_COLLECTION].find_one({"_id": oid})
    if doc is None:
        raise HTTPException(status_code=404, detail="monthly figure not found")
    return _serialize_raw_post(doc)


@app.get("/raw_posts/{code}", response_model=RawPostsDataResponse)
def get_raw_post(code: str) -> Dict[str, Any]:
    db = get_db()
    doc = db[RAW_POSTS_COLLECTION].find_one({"code": code})
    if doc is None:
        try:
            oid = _parse_object_id(code)
        except HTTPException as exc:
            raise HTTPException(
                status_code=404, detail="raw post not found"
            ) from exc
        doc = db[RAW_POSTS_COLLECTION].find_one({"_id": oid})
        if doc is None:
            raise HTTPException(status_code=404, detail="raw post not found")
    return _serialize_raw_post(doc)


@app.patch("/monthly-figures/{item_id}", response_model=RawPostsDataResponse)
def update_monthly_figure(
    item_id: str, payload: RawPostsDataUpdate
) -> Dict[str, Any]:
    db = get_db()
    oid = _parse_object_id(item_id)
    update = payload.dict(exclude_unset=True)
    if "updated_on" not in update:
        update["updated_on"] = _now_str()

    doc = db[RAW_POSTS_COLLECTION].find_one_and_update(
        {"_id": oid},
        {"$set": update},
        return_document=ReturnDocument.AFTER,
    )

    if doc is None:
        raise HTTPException(status_code=404, detail="monthly figure not found")

    return _serialize_raw_post(doc)


@app.delete("/monthly-figures/{item_id}", response_model=RawPostsDataResponse)
def delete_monthly_figure(item_id: str) -> Dict[str, Any]:
    db = get_db()
    oid = _parse_object_id(item_id)
    doc = db[RAW_POSTS_COLLECTION].find_one_and_delete({"_id": oid})
    if doc is None:
        raise HTTPException(status_code=404, detail="monthly figure not found")
    return _serialize_raw_post(doc)


def _get_codes_for_posted(db: Any, posted: bool) -> List[str]:
    cursor = db[RAW_POSTS_COLLECTION].find(
        {"posted": posted},
        {"code": 1},
    )
    return [doc["code"] for doc in cursor if doc.get("code")]


@app.get("/person-bio")
def list_person_bio(
    page: int = 1,
    page_size: int = 20,
    posted: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    if page < 1 or page_size < 1:
        raise HTTPException(
            status_code=400, detail="page and page_size must be >= 1"
        )

    db = get_db()
    skip = (page - 1) * page_size
    query: Dict[str, Any] = {}
    if posted is not None:
        codes = _get_codes_for_posted(db, posted)
        if not codes:
            return []
        query = {"code": {"$in": codes}}

    cursor = (
        db[PERSON_BIO_COLLECTION]
        .find(query)
        .sort("code", 1)
        .skip(skip)
        .limit(page_size)
    )
    return [_serialize_with_id(doc) for doc in cursor]


@app.get("/person-bio/{code}")
def get_person_bio(code: str) -> Dict[str, Any]:
    db = get_db()
    doc = db[PERSON_BIO_COLLECTION].find_one({"code": code})
    if doc is None:
        raise HTTPException(status_code=404, detail="person bio not found")
    return _serialize_with_id(doc)


@app.delete("/person-bio/{code}")
def delete_person_bio(code: str) -> Dict[str, Any]:
    db = get_db()
    doc = db[PERSON_BIO_COLLECTION].find_one_and_delete({"code": code})
    if doc is None:
        raise HTTPException(status_code=404, detail="person bio not found")
    return _serialize_with_id(doc)


@app.get("/quotes")
def list_quotes(
    page: int = 1,
    page_size: int = 20,
    posted: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    if page < 1 or page_size < 1:
        raise HTTPException(
            status_code=400, detail="page and page_size must be >= 1"
        )

    db = get_db()
    skip = (page - 1) * page_size
    query: Dict[str, Any] = {}
    if posted is not None:
        codes = _get_codes_for_posted(db, posted)
        if not codes:
            return []
        query = {"code": {"$in": codes}}

    cursor = (
        db[QUOTES_COLLECTION]
        .find(query)
        .sort("code", 1)
        .skip(skip)
        .limit(page_size)
    )
    return [_serialize_with_id(doc) for doc in cursor]


@app.get("/quotes/{code}")
def get_quotes(code: str) -> Dict[str, Any]:
    db = get_db()
    doc = db[QUOTES_COLLECTION].find_one({"code": code})
    if doc is None:
        raise HTTPException(status_code=404, detail="quotes not found")
    return _serialize_with_id(doc)


@app.delete("/quotes/{code}")
def delete_quotes(code: str) -> Dict[str, Any]:
    db = get_db()
    doc = db[QUOTES_COLLECTION].find_one_and_delete({"code": code})
    if doc is None:
        raise HTTPException(status_code=404, detail="quotes not found")
    return _serialize_with_id(doc)
