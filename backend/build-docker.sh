#!/bin/bash

# Docker build script with optimizations for handling large packages

echo "Building Docker image with optimized settings..."

# Build with increased build timeout and memory
docker build \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    --progress=plain \
    --no-cache \
    -t travel-advisory-backend:latest \
    -f Dockerfile \
    .

echo "Build complete!"

# Optional: Build with the multi-stage optimized version
# Uncomment the following to use the optimized multi-stage build
# docker build \
#     --build-arg BUILDKIT_INLINE_CACHE=1 \
#     --progress=plain \
#     --no-cache \
#     -t travel-advisory-backend:optimized \
#     -f Dockerfile.optimized \
#     .
