# ==============================================================================
# Production Dockerfile for Carbon & ESG Analytics Dashboard
# Optimized for Google Cloud Run Deployment
# ==============================================================================

FROM python:3.11-slim

# Prevent Python from buffering stdout/stderr and bytecode generation
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    STREAMLIT_SERVER_PORT=8080 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false

# Install minimal OS dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root application user for production security
RUN useradd -m -u 1000 -s /bin/bash appuser

WORKDIR /app

# Cache dependency installation layer
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code and data assets
COPY src/ ./src/
COPY data/ ./data/
COPY app.py .

# Assign ownership to non-root user
RUN chown -R appuser:appuser /app

USER appuser

# Expose standard Cloud Run HTTP port
EXPOSE 8080

# Healthcheck for container liveness
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail http://localhost:${PORT}/_stcore/health || exit 1

# Launch Streamlit with dynamic port binding for Cloud Run
CMD ["sh", "-c", "streamlit run app.py --server.port=${PORT:-8080} --server.address=0.0.0.0 --server.enableCORS=false --server.enableXsrfProtection=false"]
