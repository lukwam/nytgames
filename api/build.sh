#!/usr/bin/env bash

export BUILDKIT_PROGRESS="plain"

IMAGE="nytgames-api"

# Build from the repo root so the nytgames package is in the build context.
cd "$(dirname "$0")/.." || exit 1
docker build -f api/Dockerfile -t "${IMAGE}" .
