"""ASGI entrypoint for the Mini Exchange API.

Start with:
    uvicorn mini_exchange.api.main:app --host 0.0.0.0 --port 8000

Do NOT add --workers.  All exchange state lives in process memory.
"""

from mini_exchange.api.app import create_app

app = create_app()
