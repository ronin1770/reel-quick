#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"
source "/home/farhan/renv/bin/activate"

NODE_BIN="/root/.nvm/versions/node/v24.14.0/bin"
export PATH="$NODE_BIN:$PATH"

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

# Start ARQ sound designer worker
arq backend.workers.sound_designer_worker.WorkerSettings &
pids+=("$!")

# Start frontend (Next.js dev server)
(
  cd "$REPO_ROOT/frontend"
  "$NODE_BIN/npm" run dev
) &
pids+=("$!")

# Exit if any process dies, and stop the rest.
wait -n "${pids[@]}"
