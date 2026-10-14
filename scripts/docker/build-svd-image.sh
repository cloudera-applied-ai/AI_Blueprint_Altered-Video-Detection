#!/usr/bin/env bash
# Build SyntheticVideoDetector runtime (Bundled HF + Serverless NVCF).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${root}"

VERSION="${SVD_RUNTIME_VERSION:-1.12}"
REPO="${SVD_RUNTIME_REPO:-synthetic-video-detector}"
REGISTRY="${SVD_RUNTIME_REGISTRY:-}"

tags=(
  "${REPO}:${VERSION}"
  "${REPO}:${VERSION}-turing"
  "${REPO}:latest"
  "${REPO}:latest-turing"
)
if [[ -n "${REGISTRY}" ]]; then
  tags+=(
    "${REGISTRY}/${REPO}:${VERSION}"
    "${REGISTRY}/${REPO}:${VERSION}-turing"
    "${REGISTRY}/${REPO}:latest"
    "${REGISTRY}/${REPO}:latest-turing"
  )
fi

build_args=(docker build --platform linux/amd64 -f Dockerfile)
for tag in "${tags[@]}"; do
  build_args+=(-t "${tag}")
done
build_args+=("$@" .)

echo "Building SyntheticVideoDetector ${VERSION} (Bundled + Serverless) ..."
"${build_args[@]}"
echo "Built: ${tags[*]}"
