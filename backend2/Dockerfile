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

# Create entrypoint script for migrations and app startup
RUN echo '#!/bin/sh\n\
echo "Running database migrations..."\n\
python -c "from migrations.migrate import run_migrations; run_migrations()"\n\
echo "Starting application..."\n\
uvicorn app:app \
--host 0.0.0.0 \
--port 5000 \
--workers 1 \
--ssl-keyfile /app/ssl/key.pem \
--ssl-certfile /app/ssl/cert.pem' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Command to run migrations and start the application
CMD ["/app/entrypoint.sh"]