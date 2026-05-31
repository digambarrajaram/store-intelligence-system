FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

# Upgrades pip, suppresses root warnings, and drops temporary caches
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --root-user-action=ignore -r requirements.txt

COPY . .

CMD ["python", "worker.py"]
