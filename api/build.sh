#!/usr/bin/env bash

export BUILDKIT_PROGRESS="plain"

IMAGE="nytgames-api"

docker build -t "${IMAGE}" .
