FROM python:3.11-slim
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
COPY worker/ ./worker/
COPY services/ ./services/
COPY config/ ./config/
CMD ["python", "worker/worker.py"]
