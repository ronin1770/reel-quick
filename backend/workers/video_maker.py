"""ARQ worker for creating videos from their parts."""

from __future__ import annotations

import json, subprocess
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from arq.connections import RedisSettings
from dotenv import find_dotenv, load_dotenv

from backend.db import get_db
from backend.logger import get_logger
from backend.objects.video_automation import VideoAutomation

load_dotenv(find_dotenv())

OUTPUT_FILES_LOCATION = os.getenv("OUTPUT_FILES_LOCATION") or "./outputs"


def _parse_hms(value: str) -> float:
    parts = value.split(":")
    if len(parts) != 3:
        raise ValueError("Invalid time format")
    hours, minutes, seconds = parts
    h = int(hours)
    m = int(minutes)
    s = int(seconds)
    if h < 0 or m < 0 or s < 0 or m > 59 or s > 59:
        raise ValueError("Invalid time format")
    return float(h * 3600 + m * 60 + s)


def _safe_filename(title: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9]+", "_", title).strip("_")
    return safe or "video"


def _probe_duration_seconds(file_path: str) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError("Unable to read output duration")
    return float(result.stdout.strip())


def _format_hms(total_seconds: float) -> str:
    total = int(total_seconds)
    hours = total // 3600
    minutes = (total % 3600) // 60
    seconds = total % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _build_processing_payload(
    parts: List[Dict[str, Any]], output_name: str
) -> Dict[str, Any]:
    inputs: List[str] = []
    durations: Dict[str, Dict[str, float]] = {}
    for index, part in enumerate(parts):
        inputs.append(part["file_location"])
        durations[str(index)] = {
            "start": _parse_hms(part["start_time"]),
            "end": _parse_hms(part["end_time"]),
        }
    return {
        "inputs": inputs,
        "durations": durations,
        "output_file_name": output_name,
    }


async def process_video(ctx: Dict[str, Any], video_id: str) -> bool:
    logger = get_logger(name="instagram_reel_creation_arq")
    db = get_db()

    video = db.videos.find_one({"video_id": video_id})
    if video is None:
        logger.info("Video not found: %s", video_id)
        return False

    parts = list(
        db.video_parts.find({"video_id": video_id}).sort("part_number", 1)
    )
    if not parts:
        reason = "No video parts found for video"
        db.videos.update_one(
            {"video_id": video_id},
            {
                "$set": {
                    "status": "failed",
                    "error_reason": reason,
                    "modification_time": datetime.utcnow(),
                }
            },
        )
        logger.info(reason + ": %s", video_id)
        return False

    missing_fields = []
    required_fields = ["file_location", "start_time", "end_time", "part_number"]
    for index, part in enumerate(parts):
        missing = [field for field in required_fields if not part.get(field)]
        if missing:
            missing_fields.append(f"part_index={index} missing {', '.join(missing)}")

    if missing_fields:
        reason = "Invalid video parts: " + "; ".join(missing_fields)
        db.videos.update_one(
            {"video_id": video_id},
            {
                "$set": {
                    "status": "failed",
                    "error_reason": reason,
                    "modification_time": datetime.utcnow(),
                }
            },
        )
        logger.info(reason)
        return False

    output_dir = Path(OUTPUT_FILES_LOCATION)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Output directory: %s", output_dir)

    safe_title = _safe_filename(video.get("video_title", "video"))
    output_file_name = f"{safe_title}.mp4"
    output_path = str(output_dir / output_file_name)
    logger.info("Output file path: %s", output_path)

    db.videos.update_one(
        {"video_id": video_id},
        {
            "$set": {
                "status": "processing",
                "output_file_location": output_path,
                "error_reason": None,
                "modification_time": datetime.utcnow(),
            }
        },
    )

    payload = _build_processing_payload(parts, output_file_name)

    temp_json_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as temp_file:
            json.dump(payload, temp_file)
            temp_json_path = temp_file.name

        automation = VideoAutomation(temp_json_path)
        if not automation.read_video_config():
            raise RuntimeError("Unable to read video config")
        created = automation.process_and_create_output()
        if not created:
            raise RuntimeError("Video creation failed")
        if not Path(output_path).exists():
            raise RuntimeError("Output file was not created")

        output_duration = _probe_duration_seconds(output_path)
        output_abs_path = str(Path(output_path).resolve())
        logger.info(
            "Output created at %s UTC: %s",
            datetime.utcnow().isoformat(),
            output_abs_path,
        )
        output_size = _format_hms(output_duration)

        db.videos.update_one(
            {"video_id": video_id},
            {
                "$set": {
                    "status": "completed",
                    "output_file_location": output_path,
                    "video_size": output_size,
                    "error_reason": None,
                    "modification_time": datetime.utcnow(),
                }
            },
        )
        logger.info("Video created at %s", output_path)
        return True
    except Exception as exc:
        reason = str(exc)
        db.videos.update_one(
            {"video_id": video_id},
            {
                "$set": {
                    "status": "failed",
                    "error_reason": reason,
                    "modification_time": datetime.utcnow(),
                }
            },
        )
        logger.info("Failed to create video %s: %s", video_id, reason)
        return False
    finally:
        if temp_json_path and os.path.exists(temp_json_path):
            try:
                os.remove(temp_json_path)
            except OSError:
                pass


class WorkerSettings:
    functions = [process_video]
    redis_settings = RedisSettings.from_dsn(
        os.getenv("REDIS_URL", "redis://localhost:6379/0")
    )
