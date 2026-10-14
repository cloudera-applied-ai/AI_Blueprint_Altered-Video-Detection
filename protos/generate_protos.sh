#!/usr/bin/env bash
# Generate Python gRPC stubs for Synthetic Video Detector.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
proto_root="${root}/protos"
out="${root}/src/svd/generated"
mkdir -p "${out}"

python3 -m grpc_tools.protoc \
  -I"${proto_root}" \
  --python_out="${out}" \
  --grpc_python_out="${out}" \
  --pyi_out="${out}" \
  "${proto_root}/nvidia/maxine/syntheticvideodetector/v1/syntheticvideodetector.proto"

# Normalize grpc imports for src.svd.generated.* on PYTHONPATH.
PYTHONPATH="${root}${PYTHONPATH:+:${PYTHONPATH}}" python3 -c "from src.svd.patch_grpc_stub import ensure_grpc_stub; ensure_grpc_stub()"

touch "${out}/__init__.py"
find "${out}/nvidia" -type d -exec touch {}/__init__.py \;

echo "Generated protos under ${out}"
