# =============================================================================
# ReferralHandshake Protocol RHP-1 — Independent Runtime Monitor Dockerfile (Lane B)
# Isolation: Connects strictly as rhp_monitor (READ ONLY). Zero imports from api/.
# =============================================================================
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "psycopg[binary]>=3.1"

COPY monitor/ /app/monitor/

ENV PYTHONUNBUFFERED=1
ENV MONITOR_PORT=8001

EXPOSE 8001

HEALTHCHECK --interval=5s --timeout=2s --retries=3 \
  CMD curl -f http://localhost:8001/status || exit 1

CMD ["python", "monitor/monitor.py"]
