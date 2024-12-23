FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install -r requirements.txt gunicorn

# Copy application code
COPY backend/ .

# Create logs directory
RUN mkdir -p /app/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

# Expose port
EXPOSE 5000

# Run with Gunicorn
CMD ["gunicorn", "--config", "gunicorn_config.py", "--preload", "--pythonpath", "/app", "app:app"] 