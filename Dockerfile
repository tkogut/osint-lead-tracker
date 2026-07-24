# ============================================================
# Dockerfile — osint-lead-tracker
# Python 3.12 slim, non-root user, multi-stage build
# ============================================================

FROM python:3.12-slim AS base

# --- system deps ---
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        libglib2.0-0 \
        libnss3 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libdrm2 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxrandr2 \
        libgbm1 \
        libpango-1.0-0 \
        libasound2 \
        libxfixes3 \
        libxext6 \
        libx11-6 \
        libxcb1 \
        libxrender1 \
        libxi6 \
        libxss1 \
        libxtst6 \
        libx11-xcb1 \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- dependencies layer (cached separately) ---
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- application source ---
COPY src/ ./src/
ENV PYTHONPATH=/app/src

# --- runtime directory for SQLite data ---
RUN mkdir -p /app/data && chmod 777 /app/data

# --- non-root user ---
RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app
USER appuser

# Install Playwright Chromium browser
RUN playwright install chromium

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080", \
     "--workers", "1", "--log-level", "info"]
