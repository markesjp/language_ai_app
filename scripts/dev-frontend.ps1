$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$frontendDir = Join-Path $root "frontend"

$env:NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000/api/v1"

Set-Location $frontendDir
npm run dev
