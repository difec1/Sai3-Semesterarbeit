# Dockerfile - Optimized for stability and proper Flask execution
FROM ubuntu:22.04

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    gcc \
    g++ \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Create symbolic links for python/pip
RUN ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Fix line endings for all shell scripts
RUN find /app -name "*.sh" -type f -exec dos2unix {} \; 2>/dev/null || true

# Create necessary directories with proper permissions
RUN mkdir -p /app/chroma_data /app/data /app/frontend /app/data/text /app/data/chunks && \
    chmod -R 755 /app && \
    chmod 777 /app/chroma_data /app/data

# Make startup script executable
RUN chmod +x /app/start_docker.sh

# Expose ports
EXPOSE 5000 8000

# Health check for the Flask application
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Use startup script as entrypoint
CMD ["/app/start_docker.sh"]