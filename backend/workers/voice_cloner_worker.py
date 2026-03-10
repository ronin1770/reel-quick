"""ARQ worker for voice clone jobs.

Implementation checklist:
1) API inserts a `voice_clone_job` document with status=`queued`.
2) API enqueues `process_voice_clone_job(job_id)` on this worker queue.
3) API/WebSocket layer reads status from Mongo and pushes updates to frontend.
4) Add `voice_clone_job` collection + `job_id` unique index in DB init path.
5) Replace `sample_text` with user-provided synthesis text when API supports it.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from arq.connections import RedisSettings
from dotenv import find_dotenv, load_dotenv

from backend.db import get_db
from backend.logger import get_logger
from backend.models.voice_job_status import VOICE_CLONE_JOB_COLLECTION
from backend.workers.queue_names import VOICE_CLONE_QUEUE_NAME

load_dotenv(find_dotenv())

VOICE_CLONE_MODEL_NAME = os.getenv(
    "VOICE_CLONE_MODEL_NAME", "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
)
VOICE_CLONE_DEVICE = os.getenv("VOICE_CLONE_DEVICE", "cuda:0")
VOICE_CLONE_OUTPUT_DIR = os.getenv(
    "VOICE_CLONE_OUTPUT_DIR", "./output_files/voice_clone"
)
VOICE_CLONE_LANGUAGE = os.getenv("VOICE_CLONE_LANGUAGE", "English")
VOICE_CLONE_ATTN_IMPLEMENTATION = os.getenv(
    "VOICE_CLONE_ATTN_IMPLEMENTATION", "flash_attention_2"
)
VOICE_CLONE_SAMPLE_TEXT = os.getenv(
    "VOICE_CLONE_SAMPLE_TEXT",
    "When you feel like quitting. Remember why you started.",
)

_MODEL: Optional[Any] = None
_UNSET = object()


def _now_utc() -> datetime:
    return datetime.utcnow()


def _get_worker_logger() -> logging.Logger:
    logger = get_logger(name="instagram_reel_creation_voice_clone_arq")
    logger.setLevel(logging.INFO)
    return logger


def _job_collection() -> Any:
    db = get_db()
    return db[VOICE_CLONE_JOB_COLLECTION]


def _mark_status(
    collection: Any,
    job_id: str,
    status: str,
    *,
    progress: Optional[float] = None,
    result_path: Optional[str] = None,
    error_reason: Any = _UNSET,
    set_started: bool = False,
    set_completed: bool = False,
) -> None:
    now = _now_utc()
    update_fields: Dict[str, Any] = {
        "status": status,
        "updated_at": now,
    }
    if progress is not None:
        update_fields["progress"] = progress
    if result_path is not None:
        update_fields["result_path"] = result_path
    if error_reason is not _UNSET:
        update_fields["error_reason"] = error_reason
    if set_started:
        update_fields["started_at"] = now
    if set_completed:
        update_fields["completed_at"] = now

    collection.update_one({"job_id": job_id}, {"$set": update_fields})


def _validate_job_input(job_doc: Dict[str, Any]) -> Optional[str]:
    ref_audio_path = str(job_doc.get("ref_audio_path") or "").strip()
    ref_text = str(job_doc.get("ref_text") or "").strip()

    if not ref_audio_path:
        return "Missing ref_audio_path in voice clone job"
    if not ref_text:
        return "Missing ref_text in voice clone job"

    path = Path(ref_audio_path)
    if not path.exists():
        return f"ref_audio_path does not exist: {ref_audio_path}"
    if path.suffix.lower() != ".wav":
        return "ref_audio_path must point to a .wav file"
    return None


def _get_model() -> Any:
    global _MODEL
    if _MODEL is not None:
        return _MODEL

    import torch
    from qwen_tts import Qwen3TTSModel

    model_kwargs: Dict[str, Any] = {
        "device_map": VOICE_CLONE_DEVICE,
        "dtype": torch.bfloat16,
    }
    """attn_impl = VOICE_CLONE_ATTN_IMPLEMENTATION.strip()
    if attn_impl:
        model_kwargs["attn_implementation"] = attn_impl"""

    _MODEL = Qwen3TTSModel.from_pretrained(VOICE_CLONE_MODEL_NAME, **model_kwargs)
    return _MODEL


def _run_voice_clone(job_doc: Dict[str, Any], output_path: Path) -> str:
    """Generate output audio using the same flow as research-modules/voice_clone.py."""
    import soundfile as sf

    model = _get_model()
    ref_audio_path = str(job_doc["ref_audio_path"])
    sample_text =str(job_doc["ref_text"]).strip()
    language = str(job_doc.get("language") or VOICE_CLONE_LANGUAGE)

    wavs, sample_rate = model.generate_voice_clone(
        text=sample_text,
        language=language,
        ref_audio=ref_audio_path,
        ref_text="I was referring to the original vintage on which the Sherry is based.",
    )
    sf.write(str(output_path), wavs[0], sample_rate)
    return str(output_path.resolve())


async def process_voice_clone_job(ctx: Dict[str, Any], job_id: str) -> bool:
    logger = _get_worker_logger()
    collection = _job_collection()

    job_doc = collection.find_one({"job_id": job_id})
    if job_doc is None:
        logger.error("Voice clone job not found: %s", job_id)
        return False

    if job_doc.get("status") == "completed":
        logger.info("Voice clone job already completed: %s", job_id)
        return True

    validation_error = _validate_job_input(job_doc)
    if validation_error:
        _mark_status(
            collection,
            job_id,
            "failed",
            progress=0.0,
            error_reason=validation_error,
        )
        logger.error("Voice clone job invalid (%s): %s", job_id, validation_error)
        return False

    output_dir = Path(VOICE_CLONE_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{job_id}.wav"

    _mark_status(
        collection,
        job_id,
        "processing",
        progress=0.1,
        error_reason=None,
        set_started=True,
    )

    try:
        final_path = _run_voice_clone(job_doc, output_path)
        _mark_status(
            collection,
            job_id,
            "completed",
            progress=1.0,
            result_path=final_path,
            error_reason=None,
            set_completed=True,
        )
        logger.info("Voice clone job completed: %s output=%s", job_id, final_path)
        return True
    except Exception as exc:
        reason = str(exc)
        _mark_status(
            collection,
            job_id,
            "failed",
            progress=0.0,
            error_reason=reason,
        )
        logger.exception("Voice clone job failed: %s reason=%s", job_id, reason)
        return False


class WorkerSettings:
    functions = [process_voice_clone_job]
    queue_name = VOICE_CLONE_QUEUE_NAME
    redis_settings = RedisSettings.from_dsn(
        os.getenv("REDIS_URL", "redis://localhost:6379/0")
    )
