"""ARQ worker for text overlay jobs."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from arq.connections import RedisSettings
from dotenv import find_dotenv, load_dotenv

from backend.db import get_db
from backend.logger import get_logger
from backend.models.text_overlay_jobs import TEXT_OVERLAY_JOB_COLLECTION
from backend.models.video_text import VIDEO_OVERLAY_TEXT_COLLECTION, VideoTextModel
from backend.objects.text_overlayer import TextOverlayer
from backend.workers.queue_names import TEXT_OVERLAY_QUEUE_NAME

load_dotenv(find_dotenv())


def _now_utc() -> datetime:
    return datetime.utcnow()


def _job_collection() -> Any:
    db = get_db()
    return db[TEXT_OVERLAY_JOB_COLLECTION]


def _mark_status(
    collection: Any,
    video_id: str,
    status: str,
    *,
    status_message: Optional[str] = None,
) -> None:
    collection.update_one(
        {"video_id": video_id},
        {
            "$set": {
                "status": status,
                "status_message": status_message,
                "updated_at": _now_utc(),
            },
            "$setOnInsert": {"created_at": _now_utc()},
        },
        upsert=True,
    )


def _extract_overlays(video_text_doc: Dict[str, Any]) -> list[Dict[str, Any]]:
    config = video_text_doc.get("video_overlay_config") or {}
    overlays = config.get("overlays") or []
    if not isinstance(overlays, list):
        return []
    return [item for item in overlays if isinstance(item, dict)]


async def process_text_overlay_job(ctx: Dict[str, Any], video_id: str) -> bool:
    logger = get_logger(name="instagram_reel_creation_text_overlay_arq")
    db = get_db()
    job_collection = _job_collection()

    video_doc = db.videos.find_one({"video_id": video_id})
    if video_doc is None:
        _mark_status(job_collection, video_id, "error", status_message="video not found")
        logger.error("Text overlay job video not found: %s", video_id)
        return False

    video_status = str(video_doc.get("status") or "").strip().lower()
    if video_status != "completed":
        _mark_status(
            job_collection,
            video_id,
            "error",
            status_message="video is not completed yet",
        )
        logger.error("Text overlay video is not completed: %s", video_id)
        return False

    input_video_path = str(video_doc.get("output_file_location") or "").strip()
    if not input_video_path:
        _mark_status(
            job_collection,
            video_id,
            "error",
            status_message="output file not available on video",
        )
        logger.error("Text overlay missing source path for video: %s", video_id)
        return False

    input_path = Path(input_video_path)
    if not input_path.exists():
        _mark_status(
            job_collection,
            video_id,
            "error",
            status_message="input_video_path not found",
        )
        logger.error("Text overlay input path not found for video %s: %s", video_id, input_path)
        return False

    text_doc = db[VIDEO_OVERLAY_TEXT_COLLECTION].find_one({"video_id": video_id})
    if text_doc is None:
        _mark_status(
            job_collection,
            video_id,
            "error",
            status_message="video text overlays not found",
        )
        logger.error("Text overlay payload not found for video: %s", video_id)
        return False

    overlays = _extract_overlays(text_doc)
    if not overlays:
        _mark_status(
            job_collection,
            video_id,
            "error",
            status_message="no overlays to process",
        )
        logger.error("No overlays found for video: %s", video_id)
        return False

    requested_output_path = str(text_doc.get("output_video_path") or "").strip() or None

    _mark_status(
        job_collection,
        video_id,
        "progressing",
        status_message="processing text overlays",
    )

    overlayer = TextOverlayer()
    result = overlayer.apply_text_overlays(
        video_id=video_id,
        input_video_path=str(input_path),
        overlays=overlays,
        output_video_path=requested_output_path,
    )

    model = VideoTextModel.from_response(result)
    db[VIDEO_OVERLAY_TEXT_COLLECTION].update_one(
        {"video_id": model.video_id},
        model.to_upsert_update(),
        upsert=True,
    )

    if str(result.get("status") or "").strip().lower() == "success":
        _mark_status(
            job_collection,
            video_id,
            "finished",
            status_message=str(result.get("message") or "success"),
        )
        logger.info("Text overlay job finished for video_id=%s", video_id)
        return True

    reason = str(result.get("exception") or result.get("message") or "processing failed")
    _mark_status(
        job_collection,
        video_id,
        "error",
        status_message=reason,
    )
    logger.error("Text overlay job failed for video_id=%s: %s", video_id, reason)
    return False


class WorkerSettings:
    functions = [process_text_overlay_job]
    queue_name = TEXT_OVERLAY_QUEUE_NAME
    redis_settings = RedisSettings.from_dsn(
        os.getenv("REDIS_URL", "redis://localhost:6379/0")
    )
