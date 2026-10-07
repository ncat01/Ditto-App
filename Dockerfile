FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg util-linux \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first so the layer caches across code changes.
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY backend/scripts ./scripts
COPY backend/migrations ./migrations
COPY backend/alembic.ini ./alembic.ini
COPY backend/entrypoint.sh /usr/local/bin/ditto-entrypoint
RUN chmod 755 /usr/local/bin/ditto-entrypoint

# Run as a non-root user.
RUN useradd --create-home --uid 1000 ditto \
    && mkdir -p /data && chown -R ditto:ditto /data /app
ENTRYPOINT ["/usr/local/bin/ditto-entrypoint"]

EXPOSE 8010
CMD ["sh", "-c", "python -m alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8010} --workers 1 --no-access-log --forwarded-allow-ips ${DITTO_TRUSTED_PROXY_IPS:-127.0.0.1}"]
