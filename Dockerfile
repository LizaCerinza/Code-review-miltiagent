# syntax=docker/dockerfile:1

# ---- build: wheels del revisor y sus dependencias ---------------------------
FROM python:3.12-slim AS build
WORKDIR /src
COPY pyproject.toml README.md ./
COPY reviewer ./reviewer
RUN pip wheel --no-cache-dir --wheel-dir /wheels .

# ---- runtime -----------------------------------------------------------------
FROM python:3.12-slim

ARG VERSION=dev
ARG REVISION=unknown
LABEL org.opencontainers.image.title="code-review-multiagent" \
      org.opencontainers.image.description="Code review multiagente para pull requests (funcional, seguridad y diseño)" \
      org.opencontainers.image.source="https://github.com/LizaCerinza/Code-review-miltiagent" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# git: necesario para el modo local (`--local`) sobre un repo montado.
# safe.directory: el repo montado pertenece a otro usuario y git se negaría a leerlo.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && git config --system --add safe.directory '*'

RUN --mount=type=bind,from=build,source=/wheels,target=/wheels \
    pip install --no-cache-dir /wheels/*.whl

RUN useradd --create-home --uid 10001 reviewer
USER 10001
WORKDIR /workspace

ENTRYPOINT ["python", "-m", "reviewer"]
CMD ["--help"]
