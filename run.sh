#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

for cmd in uv node npm; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Error: '$cmd' is required but not found in PATH." >&2
    exit 1
  fi
done

cd "$PROJECT_ROOT"
uv sync

cd "$FRONTEND_DIR"
npm ci
npm run build

cd "$PROJECT_ROOT"
uv run -m app.main
