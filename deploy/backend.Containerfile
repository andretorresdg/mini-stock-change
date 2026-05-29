# Backend container for the Mini Exchange API.
#
# In-memory MVP: start a single Uvicorn process.
# The matching engine and order state live entirely in process memory.
# Multiple processes or replicas each get an independent empty book.

FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/

RUN pip install --no-cache-dir -e ".[server]"

EXPOSE 8000

CMD ["uvicorn", "mini_exchange.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
