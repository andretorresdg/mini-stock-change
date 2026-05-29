#!/usr/bin/env bash
# Build and start the full Mini Exchange MVP (API + web) with Docker Compose.
# Run from the repository root: ./scripts/run-mvp.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Starting Mini Exchange MVP (Docker Compose)"
echo "    API:  http://localhost:8000"
echo "    Web:  http://localhost:${WEB_PORT:-3000}"
echo "    OpenAPI: http://localhost:8000/openapi.json"
echo
echo "Press Ctrl+C to stop. Run './scripts/smoke-test.sh' in another terminal"
echo "once the containers are up."
echo

docker compose down --remove-orphans
docker compose up --build
