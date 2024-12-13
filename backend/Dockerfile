FROM python:3.9-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ .

# Create logs directory
RUN mkdir -p /app/logs

CMD ["python", "app.py"] 