FROM python:3.11-slim

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY services/planning-agent/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code from project root
COPY src /app/src
COPY schemas /app/schemas
COPY config /app/config

# Copy service files
COPY services/planning-agent/main.py .

# Create a non-root user
RUN groupadd -r agent && useradd -r -g agent agent
RUN chown -R agent:agent /app
USER agent

# Expose ports
EXPOSE 8000 9000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "main.py"] 