FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GENESIS_PUBLIC_MODE=true \
    GENESIS_PUBLIC_REQUIRE_HTTPS=true \
    GENESIS_PUBLIC_DATA=/tmp/genesis-public

WORKDIR /app
COPY requirements.lock pyproject.toml README.md ./
COPY genesis ./genesis
RUN python -m pip install --no-cache-dir -r requirements.lock && \
    python -m pip install --no-cache-dir --no-deps .

USER 65532:65532
EXPOSE 10000
CMD ["python", "-m", "genesis.serve"]
