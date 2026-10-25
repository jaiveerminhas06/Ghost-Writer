#!/usr/bin/env bash
# Assemble the files the Space needs into a temporary folder and push them to the Space's git repo.
#   bash deploy/push_space.sh https://huggingface.co/spaces/<you>/<name>
set -euo pipefail
SPACE_URL=$1
ROOT=$(cd "$(dirname "$0")/.." && pwd)
STAGE=$(mktemp -d)
cp -r "$ROOT/api" "$ROOT/src" "$ROOT/frontend" "$STAGE/"
rm -rf "$STAGE/frontend/node_modules" "$STAGE/frontend/dist" "$STAGE"/api/__pycache__ "$STAGE"/src/__pycache__
mkdir "$STAGE/results" "$STAGE/deploy"
cp "$ROOT/results/09_thresholds.csv" "$STAGE/results/"
cp "$ROOT/deploy/requirements-space.txt" "$STAGE/deploy/"
cp "$ROOT/deploy/Dockerfile" "$STAGE/Dockerfile"
cp "$ROOT/deploy/space_README.md" "$STAGE/README.md"
cd "$STAGE"
git init -q -b main && git add . && git commit -qm "Deploy Ghost Writer"
git push --force "$SPACE_URL" main
