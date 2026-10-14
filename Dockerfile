# syntax=docker/dockerfile:1
# Synthetic Video Detector runtime: Bundled (HF GPU) + Serverless (NVCF gRPC).
#
# Build: ./scripts/docker/build-svd-image.sh

FROM --platform=linux/amd64 docker.repository.cloudera.com/cloudera/cdsw/ml-runtime-pbj-jupyterlab-python3.13-cuda:2026.08.1-b5 AS ui-builder

USER root
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build/client/demos
COPY client/demos/package.json client/demos/package-lock.json* ./
RUN npm ci

COPY client/demos/ ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build && test -f dist/server.js

FROM --platform=linux/amd64 docker.repository.cloudera.com/cloudera/cdsw/ml-runtime-pbj-jupyterlab-python3.13-cuda:2026.08.1-b5

USER root
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ROOT=/opt/synthetic-video-detector

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates ffmpeg libgl1 git \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -sf /root/.local/bin/uv /usr/local/bin/uv

WORKDIR ${APP_ROOT}
COPY pyproject.toml README.md ./
COPY protos ./protos
COPY src ./src
COPY cai ./cai
COPY assets ./assets

RUN uv sync --extra open --extra serverless \
    && uv run bash protos/generate_protos.sh \
    && mkdir -p /var/lib/synthetic-video-detector/huggingface \
    && chown -R cdsw:cdsw ${APP_ROOT} /var/lib/synthetic-video-detector

COPY --from=ui-builder --chown=cdsw:cdsw /build/client/demos/dist ./client/demos/dist
COPY --from=ui-builder --chown=cdsw:cdsw /build/client/demos/.next ./client/demos/.next

USER cdsw
WORKDIR ${APP_ROOT}

ENV ML_RUNTIME_EDITION="SyntheticVideoDetector" \
    ML_RUNTIME_EDITOR="JupyterLab" \
    ML_RUNTIME_KERNEL="Python 3.13" \
    ML_RUNTIME_SHORT_VERSION="1.12" \
    ML_RUNTIME_MAINTENANCE_VERSION="0" \
    ML_RUNTIME_DESCRIPTION="Bundled Hugging Face GPU detection and Serverless NVIDIA NVCF"

ENV ML_RUNTIME_FULL_VERSION="${ML_RUNTIME_SHORT_VERSION}.${ML_RUNTIME_MAINTENANCE_VERSION}"

LABEL com.cloudera.ml.runtime.edition=$ML_RUNTIME_EDITION \
    com.cloudera.ml.runtime.full-version=$ML_RUNTIME_FULL_VERSION \
    com.cloudera.ml.runtime.short-version=$ML_RUNTIME_SHORT_VERSION \
    com.cloudera.ml.runtime.maintenance-version=$ML_RUNTIME_MAINTENANCE_VERSION \
    com.cloudera.ml.runtime.description=$ML_RUNTIME_DESCRIPTION \
    com.cloudera.ml.runtime.editor=$ML_RUNTIME_EDITOR

ENV PYTHONPATH="${APP_ROOT}:${APP_ROOT}/src" \
    HF_HOME=/var/lib/synthetic-video-detector/huggingface
