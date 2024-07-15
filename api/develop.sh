#!/usr/bin/env bash

SERVICE="nytgames"

IMAGE="us-central1-docker.pkg.dev/lukwam-dev/docker/${SERVICE}"
docker pull "${IMAGE}"

docker run -it --rm \
    --expose 8080 \
    --name "${SERVICE}" \
    -p 8080:8080 \
    -v "$(pwd):/app" \
    "${IMAGE}" uvicorn main:app --host 0.0.0.0 --port 8080 --reload
