FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# Generate self-signed certificate
RUN mkdir -p /app/ssl && \
    openssl req -x509 -newkey rsa:4096 -nodes \
    -keyout /app/ssl/key.pem \
    -out /app/ssl/cert.pem \
    -days 365 \
    -subj "/CN=tetrix.lol"

# Install Python dependencies first to utilize Docker cache
COPY backend2/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Copy only necessary application code
COPY backend2/app.py .
COPY backend2/core ./core
COPY backend2/models ./models
COPY backend2/routers ./routers
COPY backend2/services ./services
COPY backend2/locales ./locales
COPY backend2/gunicorn_config.py .

# Run with gunicorn
CMD ["gunicorn", "--config", "gunicorn_config.py", "--certfile", "/app/ssl/cert.pem", "--keyfile", "/app/ssl/key.pem", "app:app"]