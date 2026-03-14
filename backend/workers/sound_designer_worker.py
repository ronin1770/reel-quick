"""ARQ worker for creating custom voice files from voice-design requests."""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional

from arq.connections import RedisSettings
from dotenv import find_dotenv, load_dotenv

from backend.db import get_db
from backend.logger import get_logger
from backend.models.custom_voices import CUSTOM_VOICES_COLLECTION
from backend.models.sound_design_prompt import SOUND_DESIGN_PROMPT_COLLECTION
from backend.objects.custom_sound_designer import CustomSoundDesigner
from backend.workers.queue_names import SOUND_DESIGNER_QUEUE_NAME

load_dotenv(find_dotenv())


def _now_utc() -> datetime:
    return datetime.utcnow()


def _get_worker_logger() -> logging.Logger:
    logger = get_logger(name="instagram_reel_creation_sound_designer_worker")
    logger.setLevel(logging.INFO)
    return logger


def _prompt_collection() -> Any:
    db = get_db()
    return db[SOUND_DESIGN_PROMPT_COLLECTION]


def _custom_voices_collection() -> Any:
    db = get_db()
    return db[CUSTOM_VOICES_COLLECTION]


def _resolve_prompt_doc(collection: Any, request_id: str) -> Optional[Dict[str, Any]]:
    doc = collection.find_one(
        {"request_id": request_id, "status": "passed"},
        sort=[("updated_at", -1)],
    )
    if doc is not None:
        return doc
    return collection.find_one({"request_id": request_id}, sort=[("updated_at", -1)])


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _extract_text(prompt_doc: Dict[str, Any]) -> str:
    request_payload = _as_dict(prompt_doc.get("request_payload"))
    text = request_payload.get("text")
    if text is None:
        text = prompt_doc.get("text")
    return str(text or "").strip()


def _extract_instruction(prompt_doc: Dict[str, Any]) -> str:
    response_payload = _as_dict(prompt_doc.get("response_payload"))
    instruction = (
        response_payload.get("derived_instruction")
        or response_payload.get("derived_instructions")
        or prompt_doc.get("derived_instruction")
    )
    return str(instruction or "").strip()


def _extract_language(prompt_doc: Dict[str, Any]) -> str:
    request_payload = _as_dict(prompt_doc.get("request_payload"))
    raw = str(request_payload.get("language") or prompt_doc.get("language") or "").strip()
    language_map = {
        "en": "English",
        "zh": "Chinese",
        "ar": "Arabic",
        "ur": "Urdu",
    }
    return language_map.get(raw.lower(), raw or "English")


def _extract_generation_options(prompt_doc: Dict[str, Any]) -> Dict[str, Any]:
    request_payload = _as_dict(prompt_doc.get("request_payload"))
    generation_options = _as_dict(request_payload.get("generation_options"))
    return {
        "max_new_tokens": generation_options.get("max_new_tokens"),
        "output_format": generation_options.get("output_format"),
    }


def _normalize_output_format(value: Any) -> str:
    normalized = str(value or "wav").strip().lower()
    if normalized not in {"wav", "mp3"}:
        return "wav"
    return normalized


def _normalize_max_new_tokens(value: Any) -> int:
    if isinstance(value, int) and value > 0:
        return value
    return 2048


def _sanitize_voice_name(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("._-")
    if clean:
        return clean[:120]
    return "custom_voice"


def _build_voice_name(prompt_doc: Dict[str, Any], request_id: str) -> str:
    preset_name = str(prompt_doc.get("preset_name") or "").strip()
    if preset_name:
        return _sanitize_voice_name(f"{preset_name}_{request_id[:8]}")
    return f"custom_voice_{request_id[:8]}"


def _upsert_custom_voice(
    collection: Any,
    *,
    request_id: str,
    voice_name: str,
    instructions: str,
    output_file_location: str,
) -> None:
    now = _now_utc()
    collection.update_one(
        {"request_id": request_id},
        {
            "$set": {
                "voice_name": voice_name,
                "instructions": instructions,
                "output_file_location": output_file_location,
                "updated_at": now,
            },
            "$setOnInsert": {
                "request_id": request_id,
                "created_at": now,
            },
        },
        upsert=True,
    )


async def process_sound_design(ctx: Dict[str, Any], request_id: str) -> bool:
    logger = _get_worker_logger()
    normalized_request_id = str(request_id or "").strip()
    if not normalized_request_id:
        logger.error("Sound designer worker received an empty request_id.")
        return False

    prompt_collection = _prompt_collection()
    custom_voices_collection = _custom_voices_collection()

    prompt_doc = _resolve_prompt_doc(prompt_collection, normalized_request_id)
    if prompt_doc is None:
        logger.error(
            "Sound design prompt not found for request_id=%s",
            normalized_request_id,
        )
        return False

    logger.info(
        "Retrieved sound-design prompt request_id=%s sound_design_id=%s status=%s",
        normalized_request_id,
        prompt_doc.get("sound_design_id"),
        prompt_doc.get("status"),
    )

    input_text = _extract_text(prompt_doc)
    instructions = _extract_instruction(prompt_doc)
    if not input_text:
        logger.error(
            "Missing text in sound design prompt request_id=%s",
            normalized_request_id,
        )
        return False
    if not instructions:
        logger.error(
            "Missing derived instruction in sound design prompt request_id=%s",
            normalized_request_id,
        )
        return False

    language = _extract_language(prompt_doc)
    generation_options = _extract_generation_options(prompt_doc)
    max_new_tokens = _normalize_max_new_tokens(generation_options.get("max_new_tokens"))
    output_format = _normalize_output_format(generation_options.get("output_format"))

    logger.info(
        "Generating custom voice request_id=%s language=%s output_format=%s max_new_tokens=%s",
        normalized_request_id,
        language,
        output_format,
        max_new_tokens,
    )

    response = CustomSoundDesigner.create_sound(
        request_id=normalized_request_id,
        input_text=input_text,
        instructions=instructions,
        language=language,
        max_new_tokens=max_new_tokens,
        output_format=output_format,
    )
    logger.info(
        "Sound generation response request_id=%s payload=%s",
        normalized_request_id,
        response,
    )

    if response.get("status") != "pass":
        return False

    output_file = str(response.get("output_file") or "").strip()
    if not output_file:
        logger.error(
            "Sound generation succeeded but output_file is missing request_id=%s",
            normalized_request_id,
        )
        return False

    voice_name = _build_voice_name(prompt_doc, normalized_request_id)
    _upsert_custom_voice(
        custom_voices_collection,
        request_id=normalized_request_id,
        voice_name=voice_name,
        instructions=instructions,
        output_file_location=output_file,
    )
    logger.info(
        "Stored custom voice request_id=%s voice_name=%s output=%s",
        normalized_request_id,
        voice_name,
        output_file,
    )
    return True


class WorkerSettings:
    functions = [process_sound_design]
    queue_name = SOUND_DESIGNER_QUEUE_NAME
    redis_settings = RedisSettings.from_dsn(
        os.getenv("REDIS_URL", "redis://localhost:6379/0")
    )
