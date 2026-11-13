# Separate-OS-User Ed25519 Merkle Witness Signer (UID 1002 / rhp-sign)
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1002 rhp-sign && \
    useradd -u 1002 -g rhp-sign -m -s /bin/bash rhp-sign

WORKDIR /app

RUN pip install --no-cache-dir \
    "psycopg[binary]>=3.1.0" \
    "cryptography>=42.0.0" \
    "pydantic>=2.5.0" \
    "fastapi>=0.109.0" \
    "uvicorn>=0.27.0"

COPY signer.py /app/witness/signer.py

RUN mkdir -p /var/log/rhp-witness && chown -R 1002:1002 /var/log/rhp-witness /app

USER 1002:1002
ENV PYTHONPATH=/app

CMD ["python", "witness/signer.py"]
