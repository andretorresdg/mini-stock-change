# Manual QA checklist

Use this after `./scripts/run-mvp.sh` (or `.\scripts\run-mvp.ps1`) when the
stack is running. For automated checks first, run `./scripts/smoke-test.sh`.

## Prerequisites

- Docker Compose stack is up (`api` on port 8000, `web` on port 3000).
- `./scripts/smoke-test.sh` passes (optional but recommended).

## 1. Health and web shell

1. Open http://localhost:8000/health/live — expect `{"status":"ok"}`.
2. Open http://localhost:8000/health/ready — expect `{"status":"ok"}`.
3. Open http://localhost:3000 — the Mini Exchange header and nav appear.
4. Confirm nav links: **Submit Order**, **Order Status**, **Market**.

## 2. Submit a GTC order

1. Go to http://localhost:3000/submit-order.
2. Confirm **Order validity** defaults to **No expiration (GTC)**.
3. Fill in:
   - Broker / username: `qa-broker-a`
   - Customer document number: `11111111100`
   - Side: **ASK**
   - Stock symbol: `AAPL`
   - Unit price (USD): `10.50` (helper text mentions dot decimal format)
   - Quantity: `10`
4. Submit. The request should succeed.
5. Note the returned **Order ID** (e.g. `AAPL-O-1`).
6. Confirm validity shows **No expiration (GTC)** (not raw `null`).

## 3. Submit an order with UTC expiration

1. On the submit page, change validity to **Expires at specific UTC date/time**.
2. Pick a future date/time (helper: *Times are interpreted as UTC.*).
3. Submit a **BID** at `10.50` for symbol `AAPL`, quantity `5`, broker
   `qa-broker-b`, document `22222222200`.
4. If the order crosses the resting ASK, confirm status **FILLED** and a trade
   at the seller price (`1050` cents = $10.50).

## 4. Price input validation

1. On the submit page, enter `10,50` in **Unit price (USD)**.
2. Confirm a validation error about using a dot as the decimal separator.
3. Enter `10.50`, blur the field — value normalizes to `10.50`.
4. Submit is enabled only when the form is valid.

## 5. Order status lookup

1. Go to http://localhost:3000/status.
2. Enter broker `qa-broker-a` and the Order ID from step 2.
3. Confirm side, symbol, quantities, status, and validity display correctly.
4. For the GTC order, **Valid until** should show **No expiration (GTC)**.
5. Toggle **Auto-refresh** — status polls every 5 seconds until terminal.

## 6. Market view

1. Go to http://localhost:3000/market.
2. Enter symbol `AAPL` and load data.
3. Confirm the order book shows aggregated bid/ask levels (if any remain).
4. Confirm recent trades list includes the match from step 3 (if it occurred).

## 7. API spot checks (optional)

```bash
# GTC order via curl
curl -s -X POST http://localhost:8000/api/v1/brokers/curl-broker/orders \
  -H "Content-Type: application/json" \
  -d '{
    "document_number": "11111111100",
    "side": "BID",
    "valid_until": null,
    "symbol": "MSFT",
    "price": 2000,
    "quantity": 1
  }'

# Book snapshot
curl -s http://localhost:8000/api/v1/market/AAPL/book | python -m json.tool

# Recent trades
curl -s http://localhost:8000/api/v1/market/AAPL/trades | python -m json.tool
```

PowerShell equivalent for a GTC order:

```powershell
$body = @{
  document_number = "11111111100"
  side            = "BID"
  valid_until     = $null
  symbol          = "MSFT"
  price           = 2000
  quantity        = 1
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/brokers/curl-broker/orders" `
  -Method POST -ContentType "application/json" -Body $body
```

## 8. Restart behavior (in-memory MVP)

1. Run `docker compose restart api`.
2. Submit a new order and confirm the book starts fresh (previous resting orders
   are gone). This is expected for the in-memory MVP.

## 9. Quality gates (before committing)

From the repository root:

```bash
./scripts/check.sh
```

```powershell
.\scripts\check.ps1
```

Both backend (569+ tests, 100% coverage) and frontend (262+ tests) must pass.
