# API de CuotaFlex (motor + core simulado compatible con Fineract)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/src \
    CUOTAFLEX_DB=/app/data/cuotaflex.db PORT=8000
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config ./config
COPY src ./src
COPY scripts ./scripts
RUN useradd --create-home cuotaflex && mkdir -p /app/data && chown -R cuotaflex /app
USER cuotaflex

EXPOSE 8000
# Un solo worker: el core simulado vive en memoria (persistido en SQLite) y no se comparte entre procesos.
CMD ["sh", "-c", "uvicorn cuotaflex.api.main:app --host 0.0.0.0 --port ${PORT} --workers 1"]
