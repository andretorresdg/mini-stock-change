# Smoke-test a running Mini Exchange stack (Docker Compose or local dev).
# Defaults: API http://localhost:8000, web http://localhost:3000
$ErrorActionPreference = "Stop"

$ApiBase = if ($env:API_BASE) { $env:API_BASE } else { "http://localhost:8000" }
$WebBase = if ($env:WEB_BASE) { $env:WEB_BASE } else { "http://localhost:3000" }

function Assert-StatusOk($Response) {
    if ($Response.status -ne "ok") { throw "Expected status ok, got $($Response.status)" }
}

$live = Invoke-RestMethod -Uri "$ApiBase/health/live"
Assert-StatusOk $live
Write-Host "OK  GET /health/live"

$ready = Invoke-RestMethod -Uri "$ApiBase/health/ready"
Assert-StatusOk $ready
Write-Host "OK  GET /health/ready"

$web = Invoke-WebRequest -Uri "$WebBase/" -UseBasicParsing
if ($web.StatusCode -ne 200) { throw "Web UI returned $($web.StatusCode)" }
Write-Host "OK  GET $WebBase/ (web UI)"

$orderBody = @{
    document_number = "11111111100"
    side            = "ASK"
    valid_until     = $null
    symbol          = "SMOK"
    price           = 1000
    quantity        = 5
} | ConvertTo-Json

$create = Invoke-RestMethod -Uri "$ApiBase/api/v1/brokers/smoke-broker/orders" `
    -Method POST -ContentType "application/json" -Body $orderBody
Write-Host "OK  POST /api/v1/brokers/{broker_id}/orders (GTC)"

$orderId = $create.order_id
$status = Invoke-RestMethod -Uri "$ApiBase/api/v1/brokers/smoke-broker/orders/$orderId"
if (-not $status.order_id) { throw "Missing order_id in status response" }
Write-Host "OK  GET /api/v1/brokers/{broker_id}/orders/{order_id}"

$book = Invoke-RestMethod -Uri "$ApiBase/api/v1/market/SMOK/book"
if ($book.symbol -ne "SMOK") { throw "Unexpected book symbol" }
Write-Host "OK  GET /api/v1/market/{symbol}/book"

$trades = Invoke-RestMethod -Uri "$ApiBase/api/v1/market/SMOK/trades"
if ($null -eq $trades.trades) { throw "Missing trades array" }
Write-Host "OK  GET /api/v1/market/{symbol}/trades"

Write-Host ""
Write-Host "Smoke test passed."
