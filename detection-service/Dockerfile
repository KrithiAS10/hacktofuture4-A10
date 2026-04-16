FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/app/detection-service

WORKDIR /app

COPY detection-service/requirements.txt ./detection-service/requirements.txt
RUN pip install --no-cache-dir -r detection-service/requirements.txt

COPY lerna_shared ./lerna_shared
COPY detection-service ./detection-service

WORKDIR /app/detection-service

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
