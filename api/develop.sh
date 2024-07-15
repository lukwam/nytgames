#!/usr/bin/env bash

IMAGE="nytgames-api"

docker run -it --rm \
    --expose 8080 \
    --name "${IMAGE}" \
    -p 8080:8080 \
    -v "$(pwd):/app" \
    "${IMAGE}" uvicorn main:app --host 0.0.0.0 --port 8080 --reload
