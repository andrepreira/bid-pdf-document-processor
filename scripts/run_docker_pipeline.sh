#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_NAME="$(basename "$ROOT_DIR")"
IMAGE_NAME="bid-pdf-processor"
NETWORK_NAME="${PROJECT_NAME}_default"

cd "$ROOT_DIR"

echo "Starting PostgreSQL via docker compose..."
docker compose up -d postgres

echo "Building pipeline image..."
docker build -t "$IMAGE_NAME" .

echo "Running pipeline container..."
docker run --rm \
  --network "$NETWORK_NAME" \
  -e DATABASE_URL="postgresql://postgres:postgres@postgres:5432/bid_processor" \
  -e SOURCE_DIR="/app/source/source_files/" \
  "$IMAGE_NAME"
