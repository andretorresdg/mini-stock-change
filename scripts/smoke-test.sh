#!/usr/bin/env bash
# Smoke-test a running Mini Exchange stack (Docker Compose or local dev).
# Defaults: API http://localhost:8000, web http://localhost:3000
set -euo pipefail

API_BASE="${API_BASE:-http://localhost:8000}"
WEB_BASE="${WEB_BASE:-http://localhost:3000}"

curl -sf "${API_BASE}/health/live" | grep -q '"status":"ok"'
echo "OK  GET /health/live"

curl -sf "${API_BASE}/health/ready" | grep -q '"status":"ok"'
echo "OK  GET /health/ready"

curl -sf "${WEB_BASE}/" -o /dev/null
echo "OK  GET ${WEB_BASE}/ (web UI)"

ORDER_BODY='{
  "document_number": "11111111100",
  "side": "ASK",
  "valid_until": null,
  "symbol": "SMOK",
  "price": 1000,
  "quantity": 5
}'

CREATE_RESP="$(curl -sf -X POST "${API_BASE}/api/v1/brokers/smoke-broker/orders" \
  -H "Content-Type: application/json" \
  -d "${ORDER_BODY}")"
echo "OK  POST /api/v1/brokers/{broker_id}/orders (GTC)"

ORDER_ID="$(echo "${CREATE_RESP}" | python -c "import json,sys; print(json.load(sys.stdin)['order_id'])")"

curl -sf "${API_BASE}/api/v1/brokers/smoke-broker/orders/${ORDER_ID}" | grep -q '"order_id"'
echo "OK  GET /api/v1/brokers/{broker_id}/orders/{order_id}"

curl -sf "${API_BASE}/api/v1/market/SMOK/book" | grep -q '"symbol"'
echo "OK  GET /api/v1/market/{symbol}/book"

curl -sf "${API_BASE}/api/v1/market/SMOK/trades" | grep -q '"trades"'
echo "OK  GET /api/v1/market/{symbol}/trades"

echo
echo "Smoke test passed."
