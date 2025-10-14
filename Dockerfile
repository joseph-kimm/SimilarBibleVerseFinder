# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory in container
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY app/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app directory contents to /app in container
COPY app/ .

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
EXPOSE 8080

# Run the Flask application
CMD exec gunicorn --bind :$PORT --threads 2 --workers 1 'app:app'
