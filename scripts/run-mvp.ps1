# Build and start the full Mini Exchange MVP (API + web) with Docker Compose.
# Run from the repository root: .\scripts\run-mvp.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$WebPort = if ($env:WEB_PORT) { $env:WEB_PORT } else { "3000" }

Write-Host "==> Starting Mini Exchange MVP (Docker Compose)"
Write-Host "    API:  http://localhost:8000"
Write-Host "    Web:  http://localhost:$WebPort"
Write-Host "    OpenAPI: http://localhost:8000/openapi.json"
Write-Host ""
Write-Host "Press Ctrl+C to stop. Run '.\scripts\smoke-test.ps1' in another terminal"
Write-Host "once the containers are up."
Write-Host ""

docker compose down --remove-orphans
docker compose up --build
