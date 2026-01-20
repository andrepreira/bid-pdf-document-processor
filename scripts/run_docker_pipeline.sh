#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_NAME="$(basename "$ROOT_DIR")"

cd "$ROOT_DIR"

if [[ ! -f "$ROOT_DIR/.env" ]]; then
	echo "Creating .env from .env.example..."
	cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
fi

if ! grep -q '^POSTGRES_DB=' "$ROOT_DIR/.env"; then
	echo "POSTGRES_DB=bid_processor" >> "$ROOT_DIR/.env"
fi
if ! grep -q '^POSTGRES_USER=' "$ROOT_DIR/.env"; then
	echo "POSTGRES_USER=postgres" >> "$ROOT_DIR/.env"
fi
if ! grep -q '^POSTGRES_PASSWORD=' "$ROOT_DIR/.env"; then
	echo "POSTGRES_PASSWORD=postgres" >> "$ROOT_DIR/.env"
fi
if ! grep -q '^SOURCE_DIR=' "$ROOT_DIR/.env"; then
	echo "SOURCE_DIR=/app/source/source_files/" >> "$ROOT_DIR/.env"
fi

if grep -q '^DATABASE_URL=' "$ROOT_DIR/.env"; then
	if grep -q 'localhost:5432' "$ROOT_DIR/.env"; then
		sed -i.bak 's|localhost:5432|postgres:5432|g' "$ROOT_DIR/.env"
		rm -f "$ROOT_DIR/.env.bak"
	fi
else
	echo "DATABASE_URL=postgresql://postgres:postgres@postgres:5432/bid_processor" >> "$ROOT_DIR/.env"
fi

echo "Starting PostgreSQL and pipeline via docker compose..."
docker compose --env-file "$ROOT_DIR/.env" up -d --build postgres pipeline

echo "Streaming pipeline logs..."
docker compose --env-file "$ROOT_DIR/.env" logs -f pipeline &
LOGS_PID=$!

PIPELINE_ID=$(docker compose --env-file "$ROOT_DIR/.env" ps -q pipeline)
EXIT_CODE=$(docker wait "$PIPELINE_ID")

kill "$LOGS_PID" >/dev/null 2>&1 || true
wait "$LOGS_PID" >/dev/null 2>&1 || true

if [[ "$EXIT_CODE" -eq 0 ]]; then
	echo "Pipeline finished successfully (exit code 0)."
else
	echo "Pipeline failed with exit code $EXIT_CODE."
fi

exit "$EXIT_CODE"
