# Build stage
FROM python:3.14-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt && \
    find /root/.local -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true && \
    find /root/.local -name "*.pyc" -delete && \
    find /root/.local -name "*.dist-info" -exec rm -rf {}/RECORD {}/INSTALLER {}/REQUESTED + 2>/dev/null || true

# Final runtime stage
FROM python:3.14-slim

WORKDIR /app

# Create non-root user (UID 10001) and setup data volume directory in a single layer
RUN groupadd -g 10001 appuser && \
    useradd -u 10001 -g appuser -s /bin/sh -m appuser && \
    mkdir -p /data && \
    chown -R appuser:appuser /data /app && \
    find /usr/local -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Copy only installed python packages and application code
COPY --chown=appuser:appuser --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appuser ./app ./app

ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATA_DIR=/data

USER appuser

EXPOSE 8000

VOLUME ["/data"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
