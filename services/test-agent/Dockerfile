FROM python:3.11-slim

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy source code first (for dependency resolution)
COPY src ./src
COPY schemas ./schemas

# Copy service files
COPY services/test-agent/requirements.txt .
COPY services/test-agent/main.py .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO

# Run the application
CMD ["python", "main.py"]
