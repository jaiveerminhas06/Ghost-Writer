#!/usr/bin/env bash
# One command to run the demo:   bash scripts/demo.sh
# Builds the page if it is missing or out of date, starts ONE server (page and API together), loads every model once, opens the browser.
# Stop it with Ctrl+C. Options: PORT=8010 bash scripts/demo.sh    NO_WARMUP=1 bash scripts/demo.sh    NO_OPEN=1 bash scripts/demo.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${PORT:-8000}"
PY="${PYTHON:-python}"
URL="http://localhost:$PORT"

# Node comes from nvm on this machine
[ -s "$HOME/.nvm/nvm.sh" ] && . "$HOME/.nvm/nvm.sh"

# 1. the page (frontend/dist is not in git: it is built here)
if [ ! -f frontend/dist/index.html ] || [ -n "$(find frontend/src frontend/index.html frontend/package.json -newer frontend/dist/index.html -print -quit)" ]; then
  echo "Building the page (about 10 seconds)..."
  (cd frontend && { [ -d node_modules ] || npm ci; } && npm run build --silent)
fi

# 2. is the port free? (an old server on it would serve an old page)
if curl -s -o /dev/null -m 2 "$URL/api/meta"; then
  echo "Something is already answering on $URL. Stop it first (or run: PORT=8010 bash scripts/demo.sh)."
  exit 1
fi

# 3. the server
echo "Starting the server on $URL ..."
"$PY" -m uvicorn api.main:app --port "$PORT" --log-level warning &
SERVER=$!
trap 'kill "$SERVER" 2>/dev/null || true' EXIT INT TERM
for _ in $(seq 1 60); do
  curl -s -o /dev/null -m 2 "$URL/api/meta" && break
  kill -0 "$SERVER" 2>/dev/null || { echo "The server stopped. The message above says why."; exit 1; }
  sleep 1
done
curl -s -o /dev/null -m 2 "$URL/api/meta" || { echo "The server did not start within a minute."; exit 1; }

# 4. models (the first click would otherwise load them)
if [ -z "${NO_WARMUP:-}" ]; then echo "Loading the models (about 30 seconds the first time)..."; "$PY" scripts/warm_up.py "$URL" || true; fi

echo
echo "Ready: $URL      (Ctrl+C to stop)"
[ -z "${NO_OPEN:-}" ] && command -v xdg-open >/dev/null 2>&1 && xdg-open "$URL" >/dev/null 2>&1 || true
wait "$SERVER"
