#!/usr/bin/env bash

SERVICE="nytgames"

IMAGE="us-central1-docker.pkg.dev/lukwam-dev/docker/${SERVICE}"
docker pull "${IMAGE}"

# Mount the repo root so changes to both the API and the nytgames package
# are picked up by --reload.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

docker run -it --rm \
    --expose 8080 \
    --name "${SERVICE}" \
    -e PYTHONPATH=/app \
    -p 8080:8080 \
    -v "${ROOT}:/app" \
    -w /app/api \
    "${IMAGE}" uvicorn main:app --host 0.0.0.0 --port 8080 --reload --reload-dir /app
