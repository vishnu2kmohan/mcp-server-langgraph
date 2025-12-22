# Resilience Remediation Webhook Handler
#
# Multi-stage build for minimal production image

FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN pip install --no-cache-dir --upgrade pip

# Create requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/build/deps -r requirements.txt


FROM python:3.12-slim

WORKDIR /app

# Install kubectl for remediation scripts
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    jq \
    && curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl \
    && rm kubectl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies
COPY --from=builder /build/deps /usr/local/lib/python3.12/site-packages

# Copy application
COPY main.py .

# Copy remediation scripts
COPY ../scripts /app/scripts
RUN chmod +x /app/scripts/*.sh

# Create non-root user
RUN useradd -m -u 1000 remediation
USER remediation

# Environment defaults
ENV NAMESPACE=default \
    DRY_RUN=false \
    SCRIPTS_PATH=/app/scripts \
    COOLDOWN_SECONDS=300 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "main.py"]
