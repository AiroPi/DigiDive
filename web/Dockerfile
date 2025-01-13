# syntax=docker/dockerfile-upstream:master-labs

FROM python:3.12-alpine as build
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
WORKDIR /app
RUN --mount=type=cache,target=/var/cache/apk \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    : \
    && apk update && apk add gcc musl-dev linux-headers git \
    && uv sync --no-dev --locked \
    && :


FROM python:3.12-alpine as base
# https://docs.docker.com/reference/dockerfile/#copy---parents
COPY --parents --from=build /app/.venv /
WORKDIR /app
COPY ./src ./
COPY --parents ./alembic.ini ./alembic ./
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=0

FROM base as production
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base as debug
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
