# Build stage - Install dependencies with cache
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies with pip cache mount (BuildKit feature)
# This caches pip downloads between builds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user --no-warn-script-location -r requirements.txt

# Runtime stage - Minimal final image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data logs exports defaults

# Copy default feeds.json to /app/defaults (outside volume mount)
RUN if [ -f data/feeds.json ]; then \
        cp data/feeds.json defaults/feeds.json; \
    else \
        echo "[]" > defaults/feeds.json; \
    fi

# Copy and setup entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Use entrypoint to initialize data
ENTRYPOINT ["docker-entrypoint.sh"]

# Run the application
CMD ["python", "-u", "src/main.py"]
