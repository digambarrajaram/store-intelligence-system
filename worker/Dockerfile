# Stage 1 — install heavy dependencies (opencv, ultralytics, etc.)
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y \
    libxcb1 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY worker/requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --root-user-action=ignore opencv-python-headless && \
    pip install --no-cache-dir --root-user-action=ignore -r requirements.txt

# Stage 2 — runtime image (copy only installed packages + app code)
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libxcb1 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy all installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY worker/ ./worker/
COPY services/ ./services/
COPY config/ ./config/

CMD ["python", "worker/worker.py"]
