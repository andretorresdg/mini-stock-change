#!/usr/bin/env bash
# Run all backend and frontend quality gates from the repository root.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Backend: install dev dependencies"
python -m pip install -e ".[dev]" -q

echo "==> Backend: pytest (100% coverage required)"
python -m pytest -q

echo "==> Backend: ruff check"
python -m ruff check .

echo "==> Backend: ruff format"
python -m ruff format --check .

echo "==> Backend: mypy"
python -m mypy src

echo "==> Frontend: install dependencies"
cd web
npm ci

echo "==> Frontend: vitest"
npm run test -- --run

echo "==> Frontend: eslint"
npm run lint

echo "==> Frontend: typecheck"
npm run typecheck

echo "==> Frontend: production build"
npm run build

echo
echo "All checks passed."
