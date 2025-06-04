FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project structure
COPY . .

# Copy source code from project root
COPY ../../src /app/src
COPY ../../schemas /app/schemas
COPY ../../config /app/config

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