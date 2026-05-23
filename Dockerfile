FROM python:3.11-slim AS builder
WORKDIR /build
COPY uocra_app/requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim AS production
RUN groupadd -g 1000 appuser && useradd -u 1000 -ms /bin/bash -g appuser appuser
WORKDIR /app
COPY --from=builder /install /usr/local
COPY --chown=appuser:appuser uocra_app/ .
RUN mkdir -p /data && chown appuser:appuser /data
USER appuser
EXPOSE 8000
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:8000", "app:app"]
