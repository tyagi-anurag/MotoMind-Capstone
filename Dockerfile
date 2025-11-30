# Use official Python runtime
FROM python:3.10-slim

# Install system dependencies (often needed for audio/video processing libs)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Use shell form to access the PORT environment variable correctly
# This fixes the "failed to listen" error
CMD uvicorn api:app --host 0.0.0.0 --port ${PORT:-8080}