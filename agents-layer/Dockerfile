FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/app/agents-layer

WORKDIR /app

COPY agents-layer/requirements.txt ./agents-layer/requirements.txt
RUN pip install --no-cache-dir -r agents-layer/requirements.txt

COPY lerna_shared ./lerna_shared
COPY agents-layer ./agents-layer

WORKDIR /app/agents-layer

EXPOSE 8000

CMD ["uvicorn", "service_main:app", "--host", "0.0.0.0", "--port", "8000"]
