FROM python:3.10-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/home/appuser/.local/bin:${PATH}"

RUN echo 'Acquire::Retries "3";' > /etc/apt/apt.conf.d/80-retries && \
    echo 'Acquire::http::Dl-Limit "1000";' >> /etc/apt/apt.conf.d/80-retries && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=appuser:appuser . .

RUN mkdir -p /app/faiss_db /app/static /app/templates /app/uploads

EXPOSE 5000

COPY --chown=appuser:appuser entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT "/entrypoint.sh"