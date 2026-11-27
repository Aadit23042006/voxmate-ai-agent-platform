FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create a dedicated non-root application user
RUN groupadd --system appuser \
    && useradd --system --gid appuser --home-dir /app \
       --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app

# Run backend and Celery as non-root
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]