FROM python:3.11-slim

# System deps for psycopg2-binary and torch
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer-cached unless requirements.txt changes)
COPY requirements.txt .
# MetaTrader5 is Windows-only; exclude it for container builds
RUN pip install --no-cache-dir $(grep -v "^MetaTrader5" requirements.txt | grep -v "^#" | grep -v "^$")

COPY . .

ENV PYTHONUNBUFFERED=1

# Default: run the bot in mock mode (no MT5 creds needed)
CMD ["python", "main.py"]
