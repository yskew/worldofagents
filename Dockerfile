FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ARG INSTALL_DEV=false

COPY pyproject.toml .
RUN if [ "$INSTALL_DEV" = "true" ]; then \
        pip install --no-cache-dir ".[dev]"; \
    else \
        pip install --no-cache-dir "."; \
    fi

COPY . .
RUN chmod +x start.sh

ENV PYTHONPATH=/app
ENV PORT=8000

EXPOSE 8000

CMD ["./start.sh"]
