#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/usr/local/development/reel-quick"

cd "$REPO_ROOT"
source "$REPO_ROOT/ig_venv/bin/activate"

NODE_BIN="/root/.nvm/versions/node/v24.13.0/bin"
export PATH="$NODE_BIN:/usr/bin:/usr/local/bin"

cleanup() {
  for pid in "${pids[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait || true
}

trap cleanup SIGINT SIGTERM EXIT

pids=()

# Start API (FastAPI via Uvicorn)
uvicorn main:app --reload --app-dir backend &
pids+=("$!")

# Start ARQ video worker
arq backend.workers.video_maker.WorkerSettings &
pids+=("$!")

# Start ARQ AI worker
arq backend.workers.ai_worker.WorkerSettings &
pids+=("$!")

# Start ARQ post worker
arq backend.workers.post_worker.WorkerSettings &
pids+=("$!")

# Start ARQ voice clone worker
arq backend.workers.voice_cloner_worker.WorkerSettings &
pids+=("$!")

# Start frontend (Next.js dev server)
(
  cd "$REPO_ROOT/frontend"
  "$NODE_BIN/npm" run dev
) &
pids+=("$!")

# Exit if any process dies, and stop the rest.
wait -n "${pids[@]}"
