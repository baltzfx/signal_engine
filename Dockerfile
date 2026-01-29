# Dockerfile for Signal Engine
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create directories for data and logs
RUN mkdir -p data logs

# Debug: List what was copied
RUN ls -la /app/app/ && echo "--- Checking submodules ---" && ls -la /app/app/data/ || echo "data dir missing"

# Set working directory to app folder
WORKDIR /app/app

# Run the application
CMD ["python", "main.py"]
