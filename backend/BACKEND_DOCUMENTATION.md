# Backend Documentation (PDF-Ready)

This document summarizes the backend implementation for the Instagram Reel creation project. It is written to be PDF-friendly (clear headings, short sections, and compact lists).

## Backend technology

- **Python 3.10+**: primary backend language and video-processing logic.
- **FastAPI**: REST API framework in `backend/main.py`.
- **Uvicorn**: ASGI server used to run FastAPI.
- **MongoDB (pymongo)**: persistence for videos and video parts.
- **Redis + ARQ**: background job queue for video processing.
- **FFmpeg / FFprobe**: system binaries for media inspection and concatenation.
- **MoviePy**: Python-level video trimming and processing in `backend/objects/video_automation.py`.

## Why we selected this technology (rationale)

- **Python** enables fast iteration and strong ecosystem support for media tooling.
- **FastAPI** provides validation (Pydantic), async-friendly endpoints, and built-in OpenAPI docs.
- **MongoDB** offers a flexible document model for video and video-part metadata.
- **Redis + ARQ** keep long-running processing off the web request thread.
- **FFmpeg/FFprobe** are the most reliable, widely supported CLI tools for media inspection and muxing.
- **MoviePy** offers a Python-native API for clip trimming and effects while still using FFmpeg under the hood.

## Key prerequisites (system + services)

- **Python 3.10+**
- **FFmpeg** (must include `ffprobe` and support `libx264`)
- **MongoDB** server running (default `mongodb://localhost:27017`)
- **Redis** server running (default `redis://localhost:6379/0`)
- Sufficient disk space for uploads, temp segments, and output files.
- Environment variables (see below) set in `.env`.

### Required/expected environment variables

- `MONGODB_URI` – MongoDB connection string.
- `REDIS_URL` – Redis connection string.
- `LOG_LOCATION` – log file path for the backend logger.
- `UPLOAD_FILES_LOCATION` – filesystem path where uploads are stored (used by `/uploads`).
- `OUTPUT_FILES_LOCATION` – filesystem path for final output files.
- `INPUT_FILES_LOCATION` – base input directory used by `VideoAutomation`.

Note: `sample.env` currently uses `VIDEO_LOCATION`, but the code expects `INPUT_FILES_LOCATION` in `config.py`. Align these values to avoid missing input paths.

## Key PyPI libraries

- `fastapi` – API framework.
- `uvicorn` – ASGI server.
- `pymongo` – MongoDB driver.
- `arq` – Redis-based background job queue.
- `python-dotenv` – `.env` loading.
- `python-multipart` – upload handling for `/uploads`.
- `moviepy` – video trimming, effects, and export.
- `pydantic` – request/response models (installed via FastAPI).
- `typing-extensions` – used for `Annotated` in models (transitive dependency, but imported directly).

## Requirements.txt status

`requirements.txt` includes the core dependencies:
`pymongo`, `fastapi`, `python-multipart`, `uvicorn`, `python-dotenv`, `arq`, `moviepy`.

Additional libraries are used indirectly or imported directly:
- `pydantic` (FastAPI dependency)
- `typing-extensions` (imported in `video_part_model.py`)
- `redis` (ARQ dependency)

If you want explicit, stable installs, consider adding `pydantic` and `typing-extensions` to `requirements.txt`.

## API calls not listed in the root README

The root `README.md` already documents CRUD for `/videos` and `/video-parts` plus `/videos/{id}/enqueue`. The backend also exposes:

- `POST /uploads`
  - Accepts multipart form file upload (`file` field).
  - Rejects non-video `Content-Type`.
  - Returns `file_name`, `stored_name`, and absolute `file_location`.

FastAPI also provides automatic documentation endpoints:
- `GET /docs` (Swagger UI)
- `GET /redoc` (ReDoc)
- `GET /openapi.json` (OpenAPI schema)

## PDF generation (optional)

If you want to export this file to PDF, you can use `pandoc` locally:

```bash
pandoc backend/BACKEND_DOCUMENTATION.md -o backend/BACKEND_DOCUMENTATION.pdf
```
