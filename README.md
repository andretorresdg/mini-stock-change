# mini-exchange

An in-memory mini stock exchange MVP: a deterministic matching engine, a
FastAPI **Order Gateway**, and a React web UI. Orders, trades, and market data
live entirely in process memory — there is no PostgreSQL, ledger, or external
message broker.

## Quickstart

The fastest way to run the full stack is Docker Compose.

```bash
git clone <repo-url>
cd <repo-directory>
./scripts/run-mvp.sh
```

On **Windows PowerShell**:

```powershell
git clone <repo-url>
cd <repo-directory>
.\scripts\run-mvp.ps1
```

When the containers are up:

| Service | URL |
|---------|-----|
| Web UI | http://localhost:3000 |
| API (direct) | http://localhost:8000 |
| OpenAPI schema | http://localhost:8000/openapi.json |
| Liveness | http://localhost:8000/health/live |
| Readiness | http://localhost:8000/health/ready |

The web container proxies `/api/`, `/health/`, and `/openapi.json` to the API,
so the browser uses a single origin at port **3000**.

In a second terminal, verify the stack:

```bash
./scripts/smoke-test.sh
```

```powershell
.\scripts\smoke-test.ps1
```

Then open http://localhost:3000/submit-order and submit a test order. See
[docs/manual-qa.md](docs/manual-qa.md) for a full walkthrough.

Press **Ctrl+C** in the `run-mvp` terminal to stop. To remove containers:

```bash
docker compose down --remove-orphans
```

## What this MVP includes

### Backend

- **MatchingEngine / OrderBook** — deterministic price-time priority matching
  (integer prices and quantities only; execution at the seller price).
- **OrderGatewayService** — broker-facing submit/status flow with lazy
  expiration, broker-scoped idempotency, and in-memory metadata.
- **FastAPI** — HTTP API for orders, health checks, and public market data.

### Frontend (`web/`)

| Page | Route | Purpose |
|------|-------|---------|
| Submit Order | `/submit-order` | Place a limit order (GTC or UTC expiration) |
| Order Status | `/status` | Look up an order by broker + order ID |
| Market | `/market` | Aggregated order book snapshot and recent trades |

Details: [web/README.md](web/README.md).

### API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health/live` | Liveness probe |
| `GET` | `/health/ready` | Readiness probe |
| `POST` | `/api/v1/brokers/{broker_id}/orders` | Submit a limit order |
| `GET` | `/api/v1/brokers/{broker_id}/orders/{order_id}` | Order status |
| `GET` | `/api/v1/market/{symbol}/book` | Order book snapshot |
| `GET` | `/api/v1/market/{symbol}/trades` | Recent trades |

Full request/response reference: [docs/api.md](docs/api.md).

There is **no authentication** in this MVP. The broker ID in the URL path is
trusted as supplied.

## Developer scripts

All scripts run from the repository root.

| Script | Purpose |
|--------|---------|
| `scripts/run-mvp.sh` / `run-mvp.ps1` | Build and start API + web with Docker Compose |
| `scripts/smoke-test.sh` / `smoke-test.ps1` | Hit health, order, and market endpoints |
| `scripts/check.sh` / `check.ps1` | Run backend + frontend quality gates |

Override smoke-test targets if needed:

```bash
API_BASE=http://localhost:8000 WEB_BASE=http://localhost:3000 ./scripts/smoke-test.sh
```

## Local development (without Docker)

Use this when changing Python or TypeScript source and running tests locally.

### Backend

Requires **Python >= 3.12**.

```bash
pip install -e ".[dev,server]"
uvicorn mini_exchange.api.main:app --reload --port 8000
```

Quality gates:

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy src
```

Or run everything at once: `./scripts/check.sh` (or `.\scripts\check.ps1`).

### Frontend

Requires **Node.js >= 20** (see `web/package.json`).

```bash
cd web
npm install
npm run dev
```

The Vite dev server runs at http://localhost:5173 and calls the API at
http://localhost:8000 by default (`VITE_API_BASE_URL`). Start the backend first.

See [web/README.md](web/README.md) for page-level UI documentation.

## Important deployment constraints

> **In-memory — run one API worker only.**
>
> All exchange state (orders, trades, metadata) lives in a single process.
> Do **not** use `uvicorn --workers N`, do **not** scale the `api` service in
> Docker Compose, and do **not** add Gunicorn worker pools. Multiple workers or
> replicas each get an independent empty book.
>
> **Restarting the backend clears all orders and trades.**
>
> Horizontal scaling requires durable shared state (e.g. PostgreSQL), which is
> intentionally out of scope for this MVP.

## Matching rules (core engine)

| Rule | Description |
|------|-------------|
| Price-time priority | Best price first, then FIFO within the same price |
| BUY price | Maximum price the buyer is willing to pay |
| SELL price | Minimum price the seller is willing to accept |
| Execution price | Always the **seller** order price |
| Partial fills | Supported across multiple trades |
| FIFO | Within the same price level, older orders match first |

## Architecture

```
Browser  →  web (Nginx + React)  →  api (FastAPI + OrderGateway)  →  MatchingEngine
                                              ↓
                                    in-memory metadata + idempotency
```

- **`OrderBook`** — one symbol; owns bids/asks and deterministic matching.
- **`MatchingEngine`** — routes orders to per-symbol books (lazy creation).
- **`OrderGatewayService`** — API/gateway layer: expiration, idempotency,
  broker isolation, command sequencing, response projection.

The matching core is clock-free and deterministic. Time-based expiration is
handled at the gateway boundary.

## Manual QA

Step-by-step browser and API checks: [docs/manual-qa.md](docs/manual-qa.md).

## Further reading

- [docs/api.md](docs/api.md) — broker order API reference
- [web/README.md](web/README.md) — frontend pages, GTC/UTC validity, USD pricing
