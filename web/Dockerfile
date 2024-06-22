# syntax=docker/dockerfile-upstream:master-labs

FROM python:3.12.0-alpine as build
WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN --mount=type=cache,target=/var/cache/apk/ \
    --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    : \
    && apk add gcc musl-dev linux-headers git \
    && pip install -U pip \
    && pip install -U -r requirements.txt \
    && :

FROM python:3.12.0-alpine as base
# https://docs.docker.com/reference/dockerfile/#copy---parents
COPY --parents --from=build /opt/venv /
WORKDIR /app
COPY ./src ./
COPY --parents ./alembic.ini ./alembic ./
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=0

FROM base as prod
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base as debug
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
