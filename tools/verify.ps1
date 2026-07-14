$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot

Push-Location $Root
try {
  $env:PYTHONPATH = "$Root\backend"
  node tools/generate-contract.mjs --check
  & "$Root\.venv\Scripts\python.exe" -m pytest backend/tests
  Push-Location frontend
  try {
    npm run lint
    npm run typecheck
    npm test
    npm run build
  } finally {
    Pop-Location
  }
  git diff --check
  git diff --cached --check
  Write-Host "Windup 2D verification passed." -ForegroundColor Green
} finally {
  Pop-Location
}
