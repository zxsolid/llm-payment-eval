# Образ только с зависимостями. Код проекта монтируется в /app из compose.yaml,
# поэтому кассеты и отчёты пишутся прямо в папку проекта на хосте.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/tmp

WORKDIR /app
COPY pyproject.toml ./
COPY src/ src/
RUN pip install ".[judge]"
