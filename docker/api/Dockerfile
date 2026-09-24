FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app app
COPY requirements.txt ./
RUN pip install --no-cache-dir --requirement requirements.txt
COPY app ./app
COPY alembic.ini ./
COPY migrations ./migrations
COPY docker/api/entrypoint.sh ./docker/api/entrypoint.sh
RUN mkdir -p /app/chroma_data && chown -R app:app /app
USER app
EXPOSE 8000
CMD ["sh", "docker/api/entrypoint.sh"]
