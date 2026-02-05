#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/usr/local/development/reel-quick"

cd "$REPO_ROOT"
source "$REPO_ROOT/ig_venv/bin/activate"

# Start API (FastAPI via Uvicorn)
uvicorn main:app --reload --app-dir backend &
pid_api=$!

# Start ARQ worker
arq backend.workers.video_maker.WorkerSettings &
pid_worker=$!

# Start AI ARQ worker
arq backend.workers.ai_worker.WorkerSettings &
pid_ai_worker=$!

# Start frontend (Next.js dev server)
cd "$REPO_ROOT/frontend"
NODE_BIN="/root/.nvm/versions/node/v24.13.0/bin"
export PATH="$NODE_BIN:/usr/bin:/usr/local/bin"

cd /usr/local/development/reel-quick/frontend

"$NODE_BIN/npm" run dev
pid_frontend=$!

trap 'kill "$pid_api" "$pid_worker" "$pid_ai_worker" "$pid_frontend" 2>/dev/null || true; wait || true' SIGINT SIGTERM

# Exit if any process dies, and stop the rest.
wait -n "$pid_api" "$pid_worker" "$pid_ai_worker" "$pid_frontend"
exit_code=$?
kill "$pid_api" "$pid_worker" "$pid_ai_worker" "$pid_frontend" 2>/dev/null || true
wait || true
exit "$exit_code"
