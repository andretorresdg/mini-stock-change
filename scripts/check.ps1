# Run all backend and frontend quality gates from the repository root.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

function Invoke-Step {
    param(
        [string]$Label,
        [scriptblock]$Command
    )
    Write-Host "==> $Label"
    # npm/pip may write warnings to stderr without failing; rely on exit code.
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $Command 2>&1 | Out-Host
    $exit = $LASTEXITCODE
    $ErrorActionPreference = $prev
    if ($exit -ne 0) {
        throw "Step failed (exit $exit): $Label"
    }
}

Invoke-Step "Backend: install dev dependencies" { python -m pip install -e ".[dev]" -q }
Invoke-Step "Backend: pytest (100% coverage required)" { python -m pytest -q }
Invoke-Step "Backend: ruff check" { python -m ruff check . }
Invoke-Step "Backend: ruff format" { python -m ruff format --check . }
Invoke-Step "Backend: mypy" { python -m mypy src }

Set-Location web
Invoke-Step "Frontend: install dependencies" { npm ci }
Invoke-Step "Frontend: vitest" { npm run test -- --run }
Invoke-Step "Frontend: eslint" { npm run lint }
Invoke-Step "Frontend: typecheck" { npm run typecheck }
Invoke-Step "Frontend: production build" { npm run build }

Write-Host ""
Write-Host "All checks passed."
