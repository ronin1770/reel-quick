# Reel Quick production Docker Compose

## Included services
- `nginx`: reverse proxy for frontend and backend
- `frontend`: Next.js production server
- `api`: FastAPI app
- `worker-video`: ARQ worker for `backend.workers.video_maker.WorkerSettings`
- `worker-post`: ARQ worker for `backend.workers.post_worker.WorkerSettings`
- `worker-ai`: ARQ worker for `backend.workers.ai_worker.WorkerSettings`
- `worker-text-overlay`: ARQ worker for `backend.workers.text_overlay_worker.WorkerSettings`
- `worker-voice-cloner`: GPU profile worker for `backend.workers.voice_cloner_worker.WorkerSettings`
- `worker-sound-designer`: GPU profile worker for `backend.workers.sound_designer_worker.WorkerSettings`
- `redis`: ARQ queue backend
- `mongo`: app database

## Why there are two backend images
The repo's root requirements include the regular API stack plus heavy CUDA/Torch/TTS packages. For production, the Compose keeps the core API and lighter workers on a slim Python image and moves GPU/TTS workers into a dedicated CUDA image.

## Run CPU-only production stack
```bash
docker compose -f docker/docker-compose.yml up -d --build
```

## Run with GPU workers
```bash
docker compose -f docker/docker-compose.yml --profile gpu up -d --build
```

## Paths and volumes
- uploaded/generated media: named volumes `video_files`, `output_files`
- logs: named volume `backend_logs`
- worker control/runtime files: named volume `worker_runtime`

## Notes
- Nginx routes `/api/*` to FastAPI and `/` to Next.js.
- `/outputs/` is exposed by Nginx for generated assets.
- Healthchecks are included for Mongo, Redis, and the API.
- For public deployment, terminate TLS in front of Nginx or extend the Nginx config with certificates.
