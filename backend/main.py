"""FastAPI entrypoint."""

from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict, List
from uuid import uuid4

from arq import create_pool
from arq.connections import RedisSettings
from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from db import get_db, init_db
from logger import get_logger
from models.video_model import VideoCreate, VideoSchema, VideoUpdate
from models.video_part_model import (
    VideoPartCreate,
    VideoPartSchema,
    VideoPartUpdate,
)

app = FastAPI()
logger = get_logger(log_path="./log/fastapi.log", name="instagram_reel_creation_fastapi")

load_dotenv(find_dotenv())
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
UPLOAD_FILES_LOCATION = os.getenv("UPLOAD_FILES_LOCATION", "./uploads")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    logger.info("Database initialized")


def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


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


@app.post("/uploads")
def upload_video_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="file is required")
    if file.content_type and not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="only video uploads are supported")

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
    print(f"List Vides")
    try:
        db = get_db()
        docs = [_serialize(doc) for doc in db.videos.find({})]
        logger.info(f"Documents length: {len(docs)}\n{docs}")
        return docs
    except Exception as exc:
        print(f"Exception is: {str(exc)}")
        logger.info("Failed to list videos: %s", exc)
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
        job = await redis.enqueue_job("process_video", video_id)
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
