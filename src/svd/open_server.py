"""Local Hugging Face open-weights detector HTTP service (OPEN deploy mode)."""

from __future__ import annotations

import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

from src.svd.model_catalog import resolve_consensus_strategy, resolve_open_models
from src.svd.open_inference import LoadedModel, load_open_models, score_video_with_consensus
from src.svd.client import classification_threshold

DEFAULT_PORT = 8090

_loaded: list[LoadedModel] = []


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _loaded
    _loaded = load_open_models()
    yield
    _loaded = []


app = FastAPI(title="SVD Open Weights Detector", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, object]:
    specs = resolve_open_models()
    return {
        "status": "ok",
        "model_count": len(_loaded),
        "consensus": resolve_consensus_strategy(),
        "models": [
            {
                "hf_model_id": m.hf_model_id,
                "kind": m.kind,
                "preset_id": m.preset_id,
            }
            for m in _loaded
        ],
        "configured": specs,
    }


@app.post("/v1/detect")
async def detect(file: UploadFile = File(...)) -> JSONResponse:
    if not _loaded:
        return JSONResponse({"error": "Models not loaded"}, status_code=503)
    suffix = Path(file.filename or "upload.mp4").suffix or ".mp4"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
    try:
        threshold = classification_threshold()
        result = score_video_with_consensus(
            tmp_path,
            _loaded,
            threshold=threshold,
        )
        return JSONResponse(result)
    finally:
        tmp_path.unlink(missing_ok=True)


def main() -> None:
    port = int(os.environ.get("SVD_OPEN_PORT", DEFAULT_PORT))
    uvicorn.run(
        "src.svd.open_server:app",
        host="127.0.0.1",
        port=port,
        log_level=os.environ.get("SVD_OPEN_LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    main()
