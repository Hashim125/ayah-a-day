# Multi-stage Docker build for Ayah App

# Build stage
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml ./
RUN pip install --no-cache-dir build wheel

# Build the package
COPY . .
RUN python -m build

# Production stage
FROM python:3.11-slim as production

# Create non-root user
RUN groupadd -r ayah && useradd -r -g ayah ayah

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy built package from builder stage
COPY --from=builder /app/dist/*.whl /tmp/

# Install Python dependencies
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

# Install additional production dependencies
RUN pip install --no-cache-dir gunicorn

# Create necessary directories
RUN mkdir -p /app/data /app/cache /app/logs /app/static /app/templates \
    && chown -R ayah:ayah /app

# Copy data files (if they exist)
COPY --chown=ayah:ayah data/ /app/data/
COPY --chown=ayah:ayah static/ /app/static/
COPY --chown=ayah:ayah templates/ /app/templates/

# Copy configuration
COPY --chown=ayah:ayah config/ /app/config/

# Switch to non-root user
USER ayah

# Set environment variables
ENV PYTHONPATH=/app
ENV FLASK_APP=src.ayah_app.app:create_app
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Expose port
EXPOSE 5000

# Default command
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--worker-class", "sync", "--timeout", "120", "--keep-alive", "2", "--max-requests", "1000", "--max-requests-jitter", "100", "--access-logfile", "/app/logs/access.log", "--error-logfile", "/app/logs/error.log", "--log-level", "info", "src.ayah_app.app:create_app()"]