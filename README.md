# Reel Quick

![Project Logo](frontend/public/logo-rectangle.jpg)

This repository provides an **open-source, end-to-end solution for fast and effortless Instagram Reel creation**. It enables you to upload video clips, trim them, and seamlessly merge multiple segments into a single, high-quality reel—perfect for creating engaging short-form content.

The project is designed with **performance, simplicity, and automation** in mind. There are **no accounts, logins, or credentials required**, making it ideal for developers, content creators, and automation workflows.

### ✨ Key Features

* Upload, trim, and merge multiple video files
* Fast, asynchronous video processing
* Clean web-based interface for reel creation
* No authentication or third-party dependencies
* Completely free and open source

### 🛠️ Tech Stack

* **Python 3.10+** – backend and processing logic
* **Uvicorn** – high-performance ASGI web server
* **Next.js** – modern frontend framework
* **ARQ (Async Redis Queue)** – background video processing
* **FFmpeg / FFprobe** – video manipulation and metadata inspection

### 🆓 License

This project is **free to use**, modify, and extend under an open-source license.

## 💡 Why I Created This Repository

I’m a **backend developer and DevOps engineer**, and I run a motivation-themed Instagram page (**@motivation_nitrous**). Creating content for the page typically involves stitching together multiple video clips to produce short, engaging reels.

Initially, I handled this workflow using **JSON configuration files in VS Code**. While functional, the process quickly became **time-consuming and inefficient**. Each reel required manually selecting files, copying paths, editing JSON structures, and fine-tuning scene boundaries to get the desired result. As content volume grew, this approach no longer scaled.

This repository was created to **automate and streamline the reel-creation workflow**, replacing repetitive manual steps with a faster, more intuitive system—without sacrificing flexibility or control.

---

## 🚧 Current Status

* ✅ **Backend API (FastAPI)** — completed
* ✅ **Frontend (Next.js)** — core video creation workflow implemented
* ⚠️ **Background Worker (ARQ-based)** — currently under active development

---

## 🗺️ Roadmap

Planned features and enhancements include:

* Bulk video creation from a single directory or input path
* Support for **image-based posts** (static Instagram content)
* GPT-powered text generation for Instagram image posts (via API key)
* Custom video transitions and effects between scenes
* In-browser image editing tools (crop, rotate, annotate, filters)
* Webhook support for automation and external integrations


## Prerequisites (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg redis-server
```

MongoDB server is required for the `instagram_reel_creator` database.

## Environment

Create `.env` in the repo root:

```
MONGODB_URI=mongodb://localhost:27017
LOG_LOCATION=./log/backend.log
REDIS_URL=redis://localhost:6379/1
OUTPUT_FILES_LOCATION=./outputs
```

## Run the API

```bash
pip install -r requirements.txt

uvicorn main:app --reload --app-dir backend
```

## Run the worker

```bash
cd /usr/local/development/instagram-reel-creation
```


```bash
arq backend.workers.video_maker.WorkerSettings
```

## Sample cURL

Create a video:

```bash
curl -X POST http://127.0.0.1:8000/videos \
  -H "Content-Type: application/json" \
  -d '{
    "video_title": "My first reel",
    "video_introduction": "Short intro",
    "video_tags": ["travel", "daily"],
    "active": true
  }'
```

List videos:

```bash
curl -X GET http://127.0.0.1:8000/videos
```

Get a video by id:

```bash
curl -X GET http://127.0.0.1:8000/videos/<video_id>
```

Update a video:

```bash
curl -X PATCH http://127.0.0.1:8000/videos/<video_id> \
  -H "Content-Type: application/json" \
  -d '{
    "video_title": "Updated reel title",
    "active": false
  }'
```

Delete a video:

```bash
curl -X DELETE http://127.0.0.1:8000/videos/<video_id>
```

Enqueue a video for processing:

```bash
curl -X POST http://127.0.0.1:8000/videos/<video_id>/enqueue
```

Create a video part:

```bash
curl -X POST http://127.0.0.1:8000/video-parts \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "<video_id_from_create>",
    "file_part_name": "clip_01.mp4",
    "part_number": 1,
    "file_location": "/absolute/path/to/clip_01.mp4",
    "start_time": "00:00:40",
    "end_time": "00:00:50",
    "selected_duration": 8.0,
    "active": true
  }'
```

List video parts:

```bash
curl -X GET http://127.0.0.1:8000/video-parts
```

Get a video part by id:

```bash
curl -X GET http://127.0.0.1:8000/video-parts/<video_parts_id>
```

Update a video part:

```bash
curl -X PATCH http://127.0.0.1:8000/video-parts/<video_parts_id> \
  -H "Content-Type: application/json" \
  -d '{
    "file_part_name": "clip_01_trimmed.mp4",
    "selected_duration": 7.5
  }'
```

Delete a video part:

```bash
curl -X DELETE http://127.0.0.1:8000/video-parts/<video_parts_id>
```
