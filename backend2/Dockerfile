FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Generate self-signed certificate
RUN mkdir -p /app/ssl && \
    openssl req -x509 -newkey rsa:4096 -nodes \
    -keyout /app/ssl/key.pem \
    -out /app/ssl/cert.pem \
    -days 365 \
    -subj "/CN=tetrix.lol"

# Copy requirements first to leverage Docker cache
COPY backend2/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend2/ .

# Command to run the application
CMD WORKERS=$(($(nproc) * 2 + 1)) && \
    uvicorn app:app \
    --host 0.0.0.0 \
    --port 5000 \
    --workers $WORKERS \
    --ssl-keyfile /app/ssl/key.pem \
    --ssl-certfile /app/ssl/cert.pem