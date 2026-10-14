"""NVIDIA Cloud Functions gRPC detection (optional serverless extra)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Iterator

import grpc

from src.svd.client import ClipResult, DetectionResult, _expit, classification_threshold
from src.svd.patch_grpc_stub import ensure_grpc_stub

ensure_grpc_stub()

from src.svd.generated.nvidia.maxine.syntheticvideodetector.v1 import (  # noqa: E402
    syntheticvideodetector_pb2,
    syntheticvideodetector_pb2_grpc,
)
from src.svd.nvcf import (
    DEFAULT_NVCF_GRPC_HOST,
    DEFAULT_NVCF_GRPC_PORT,
    intercept_channel_with_metadata,
    is_nvcf_endpoint,
    nvcf_grpc_metadata,
    svd_nvcf_function_id,
)

DATA_CHUNK_SIZE = 2 * 1024 * 1024


def _local_endpoint(endpoint: str) -> bool:
    host = endpoint.partition(":")[0].strip().lower()
    return host in {"127.0.0.1", "localhost", "0.0.0.0"}


def resolve_svd_target() -> tuple[str, bool, tuple[tuple[str, str], ...] | None]:
    endpoint = os.environ.get("SVD_SERVER", "").strip()
    if endpoint and not _local_endpoint(endpoint):
        host, _, port = endpoint.partition(":")
        port = port or DEFAULT_NVCF_GRPC_PORT
        target = f"{host}:{port}"
        if is_nvcf_endpoint(host):
            api_key = os.environ.get("NGC_API_KEY", "").strip()
            if not api_key:
                raise RuntimeError("NGC_API_KEY is required for serverless NVCF mode")
            return target, True, nvcf_grpc_metadata(api_key, svd_nvcf_function_id())
    host = os.environ.get("NVIDIA_SERVERLESS_GRPC_HOST", DEFAULT_NVCF_GRPC_HOST)
    port = os.environ.get("NVIDIA_SERVERLESS_GRPC_PORT", DEFAULT_NVCF_GRPC_PORT)
    api_key = os.environ.get("NGC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("NGC API key is required for serverless mode")
    return f"{host}:{port}", True, nvcf_grpc_metadata(api_key, svd_nvcf_function_id())


def _video_chunks(video_path: Path) -> Iterator[syntheticvideodetector_pb2.DetectSyntheticVideoRequest]:
    with video_path.open("rb") as handle:
        while True:
            chunk = handle.read(DATA_CHUNK_SIZE)
            if not chunk:
                break
            yield syntheticvideodetector_pb2.DetectSyntheticVideoRequest(video_file_data=chunk)


def detect_video_serverless(
    path: Path,
    *,
    timeout_s: int = 600,
    on_progress: Callable[[dict[str, object]], None] | None = None,
) -> DetectionResult:
    if on_progress:
        on_progress({"type": "phase", "phase": "connecting", "message": "Connecting to detector…"})

    target, use_tls, metadata = resolve_svd_target()
    if use_tls:
        channel = grpc.secure_channel(target, grpc.ssl_channel_credentials())
    else:
        channel = grpc.insecure_channel(target)
    if metadata:
        channel = intercept_channel_with_metadata(channel, metadata)

    if on_progress:
        on_progress({"type": "phase", "phase": "uploading", "message": "Sending video to detector…"})

    stub = syntheticvideodetector_pb2_grpc.SyntheticVideoDetectorServiceStub(channel)
    clip_results: list[ClipResult] = []
    final_probability = 0.0
    final_logit = 0.0
    total_clips = 0
    csv_data = ""

    responses = stub.DetectSyntheticVideo(_video_chunks(path), timeout=timeout_s)
    analyzing_sent = False
    for response in responses:
        which = response.WhichOneof("stream_output")
        if which == "clip_result":
            clip = response.clip_result
            clip_results.append(ClipResult(index=clip.index, logit=clip.logit))
            if on_progress:
                if not analyzing_sent:
                    analyzing_sent = True
                    on_progress(
                        {
                            "type": "phase",
                            "phase": "analyzing",
                            "message": "Analyzing video clips…",
                        }
                    )
                score = _expit(clip.logit)
                on_progress(
                    {
                        "type": "clip",
                        "index": clip.index,
                        "logit": clip.logit,
                        "score": round(score, 4),
                        "clips_done": len(clip_results),
                    }
                )
        elif which == "final_result":
            final = response.final_result
            final_logit = final.logit
            final_probability = final.probability or _expit(final.logit)
            total_clips = final.total_clips
            csv_data = final.csv_data or ""
            if on_progress:
                on_progress(
                    {
                        "type": "phase",
                        "phase": "finalizing",
                        "message": "Summarizing results…",
                        "total_clips": total_clips,
                    }
                )
        elif which == "keepalive":
            continue

    channel.close()

    score = final_probability if final_probability else _expit(final_logit)
    return DetectionResult(
        probability=score,
        logit=final_logit,
        total_clips=total_clips,
        csv_data=csv_data,
        clip_results=clip_results,
        is_synthetic=score >= classification_threshold(),
        synthetic_score_percent=round(score * 100, 1),
    )
