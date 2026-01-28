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

# Set Python path
ENV PYTHONPATH=/app

# Run the application
CMD ["python", "-m", "app.main"]
