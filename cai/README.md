# Synthetic Video Detector on Cloudera AI Workbench

CAI deployment overlay: **Bundled** Hugging Face GPU apps and **Serverless** NVIDIA NVCF.

## Architecture

Three CAI applications — not three copies of the same UI:

| App | Role |
|-----|------|
| **Launchpad** | Configure env vars and **generate** standalone runtime apps |
| **Bundled runtime** | HF model HTTP service + Detect/Demo UI (GPU, one pod) |
| **Serverless runtime** | NVCF gRPC + Detect/Demo UI (CPU) |

### Bundled runtime (single container)

The runtime image includes PyTorch, Transformers, and the blueprint open detector server (`src/svd/open_server.py`). At runtime the open app:

1. Reads config from **CML application environment variables** (set by Launchpad at deploy time)
2. Starts **`python -m src.svd.open_server`** on `SVD_OPEN_PORT` (default `8090`)
3. Waits for `/health`, then wires `SVD_OPEN_SERVER=127.0.0.1:<port>` for the UI
4. Serves the **Next.js UI** on `CDSW_APP_PORT`

First start may download model weights from Hugging Face into the project cache.

### Serverless runtime

Same UI artifact; `launch_serverless_app.py` wires NVCF endpoints and starts the UI. No local GPU model.

## Modes

| Mode | GPU | Inference |
|------|-----|-----------|
| **BUNDLED** | 1× GPU | Local HTTP on `SVD_OPEN_PORT` |
| **SERVERLESS** | 0 | `grpc.nvcf.nvidia.com:443` |

## Build runtime image

```bash
./scripts/docker/build-svd-image.sh
```

Register **SyntheticVideoDetector** in Runtime Catalog (`cai/runtime/METADATA.yaml`).

## AMP tasks

1. Install Python deps + protos
2. Build Next.js UI
3. Start Launchpad

From Launchpad: configure → deploy Serverless and/or Bundled runtime apps.

## Open model presets (Launchpad)

Curated in `cai/config/open_model_catalog.json`:

| Preset | Hugging Face ID | Role |
|--------|-----------------|------|
| **VideoMAE Deepfake Detector** (default) | [eftt/VideoMae-ffc23-deepfake-detector](https://huggingface.co/eftt/VideoMae-ffc23-deepfake-detector) | Video-native temporal model (16 frames per window) |
| **AI vs Deepfake vs Real** | [prithivMLmods/AI-vs-Deepfake-vs-Real-v2.0](https://huggingface.co/prithivMLmods/AI-vs-Deepfake-vs-Real-v2.0) | SigLIP 3-class, frame sampling |
| **Deepfake vs Real (ViT)** | [dima806/deepfake_vs_real_image_detection](https://huggingface.co/dima806/deepfake_vs_real_image_detection) | Lightweight binary, fast cold start |

| Setting | Default |
|---------|---------|
| Serve port | `8090` |
| HF token | Optional for public models |

**Bundled** does not call NVIDIA inference—the HF model runs in your GPU app.

**Serverless** uses NGC key, NVCF function ID, and gRPC to `grpc.nvcf.nvidia.com`.

## Troubleshooting

| Issue | Action |
|-------|--------|
| HF download fails | Set `HF_TOKEN` for gated models; check outbound HTTPS |
| GPU not visible | Confirm GPU quota on the deployed application |
| Model server timeout | Inspect `cai/config/svd_open_model.log` and `nim_startup.json` |
| Serverless auth error | Confirm `SVD_NVIDIA_FUNCTION_ID` and `NGC_API_KEY` on deployed app |
