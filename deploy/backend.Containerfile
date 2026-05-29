# Backend container for the Mini Exchange API.
#
# In-memory MVP: start a single Uvicorn process.
# The matching engine and order state live entirely in process memory.
# Multiple processes or replicas each get an independent empty book.

FROM python:3.12-slim

LABEL org.opencontainers.image.title="Mini Exchange API"
LABEL org.opencontainers.image.description="FastAPI order gateway and in-memory matching engine for the deterministic mini stock exchange MVP."
LABEL org.opencontainers.image.source="https://github.com/andretorresdg/mini-stock-change"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

COPY pyproject.toml ./
COPY requirements/server.lock requirements/server.lock
COPY src/ ./src/

RUN pip install --no-cache-dir -r requirements/server.lock \
    && pip install --no-cache-dir --no-deps -e .

EXPOSE 8000

CMD ["uvicorn", "mini_exchange.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
