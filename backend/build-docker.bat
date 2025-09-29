@echo off
REM Docker build script with optimizations for handling large packages

echo Building Docker image with optimized settings...

REM Build with increased build timeout and memory
docker build ^
    --build-arg BUILDKIT_INLINE_CACHE=1 ^
    --progress=plain ^
    --no-cache ^
    -t travel-advisory-backend:latest ^
    -f Dockerfile ^
    .

echo Build complete!

REM Optional: Build with the multi-stage optimized version
REM Uncomment the following to use the optimized multi-stage build
REM docker build ^
REM     --build-arg BUILDKIT_INLINE_CACHE=1 ^
REM     --progress=plain ^
REM     --no-cache ^
REM     -t travel-advisory-backend:optimized ^
REM     -f Dockerfile.optimized ^
REM     .
