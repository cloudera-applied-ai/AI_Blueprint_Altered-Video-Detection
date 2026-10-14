# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""NVIDIA Cloud Functions (NVCF) gRPC client helpers."""

from __future__ import annotations

import collections
import os
from collections.abc import Callable
from typing import Any

import grpc

DEFAULT_SVD_NVCF_FUNCTION_ID = "847b6e53-0133-452d-ab85-d7acf3ace723"
DEFAULT_NVCF_GRPC_HOST = "grpc.nvcf.nvidia.com"
DEFAULT_NVCF_GRPC_PORT = "443"


class _ClientCallDetails(
    collections.namedtuple(
        "_ClientCallDetails",
        ("method", "timeout", "metadata", "credentials", "wait_for_ready", "compression"),
    ),
    grpc.ClientCallDetails,
):
    pass


def resolve_nvcf_function_id(env_var: str = "SVD_NVIDIA_FUNCTION_ID", default: str = "") -> str:
    return os.environ.get(env_var, "").strip() or default or DEFAULT_SVD_NVCF_FUNCTION_ID


def svd_nvcf_function_id() -> str:
    return resolve_nvcf_function_id()


def nvcf_grpc_metadata(ngc_api_key: str, function_id: str) -> tuple[tuple[str, str], ...]:
    return (
        ("authorization", f"Bearer {ngc_api_key}"),
        ("function-id", function_id),
    )


def is_nvcf_endpoint(host: str) -> bool:
    return "nvcf.nvidia.com" in host.strip().lower()


class _MetadataClientInterceptor(
    grpc.UnaryUnaryClientInterceptor,
    grpc.UnaryStreamClientInterceptor,
    grpc.StreamUnaryClientInterceptor,
    grpc.StreamStreamClientInterceptor,
):
    def __init__(self, metadata: tuple[tuple[str, str], ...]) -> None:
        self._metadata = metadata

    def _inject(
        self,
        continuation: Callable[..., Any],
        client_call_details: grpc.ClientCallDetails,
        request_or_iterator: Any,
    ) -> Any:
        metadata = list(client_call_details.metadata or [])
        metadata.extend(self._metadata)
        details = _ClientCallDetails(
            client_call_details.method,
            client_call_details.timeout,
            metadata,
            client_call_details.credentials,
            client_call_details.wait_for_ready,
            getattr(client_call_details, "compression", None),
        )
        return continuation(details, request_or_iterator)

    def intercept_unary_unary(self, continuation, client_call_details, request):
        return self._inject(continuation, client_call_details, request)

    def intercept_unary_stream(self, continuation, client_call_details, request):
        return self._inject(continuation, client_call_details, request)

    def intercept_stream_unary(self, continuation, client_call_details, request_iterator):
        return self._inject(continuation, client_call_details, request_iterator)

    def intercept_stream_stream(self, continuation, client_call_details, request_iterator):
        return self._inject(continuation, client_call_details, request_iterator)


def intercept_channel_with_metadata(
    channel: grpc.Channel,
    metadata: tuple[tuple[str, str], ...],
) -> grpc.Channel:
    if not metadata:
        return channel
    return grpc.intercept_channel(channel, _MetadataClientInterceptor(metadata))
