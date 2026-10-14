"""Repair grpc stub imports after protoc (grpc_tools emits package-absolute aliases)."""

from __future__ import annotations

import re
from pathlib import Path

_LONG_ALIAS = "nvidia_dot_maxine_dot_syntheticvideodetector_dot_v1_dot_syntheticvideodetector__pb2"
_SHORT_ALIAS = "syntheticvideodetector__pb2"
_GRPC_STUB = (
    Path(__file__).resolve().parent
    / "generated"
    / "nvidia"
    / "maxine"
    / "syntheticvideodetector"
    / "v1"
    / "syntheticvideodetector_pb2_grpc.py"
)


def ensure_grpc_stub() -> Path:
    """Patch the checked-in grpc stub if protoc left broken absolute aliases."""
    path = _GRPC_STUB
    if not path.is_file():
        return path
    text = path.read_text()
    if _LONG_ALIAS not in text and f"from . import syntheticvideodetector_pb2 as {_SHORT_ALIAS}" in text:
        return path
    text = text.replace(_LONG_ALIAS, _SHORT_ALIAS)
    text = re.sub(
        r"^from nvidia\.maxine\.syntheticvideodetector\.v1 import syntheticvideodetector_pb2.*\n",
        f"from . import syntheticvideodetector_pb2 as {_SHORT_ALIAS}\n",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r"^import syntheticvideodetector_pb2.*\n",
        f"from . import syntheticvideodetector_pb2 as {_SHORT_ALIAS}\n",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    path.write_text(text)
    return path
