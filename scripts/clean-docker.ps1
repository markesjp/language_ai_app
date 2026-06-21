$ErrorActionPreference = "Stop"

Write-Host "Cleaning dangling Docker images..." -ForegroundColor Cyan
& docker image prune -f

Write-Host "Cleaning build cache older than 24h..." -ForegroundColor Cyan
& docker builder prune -f --filter "until=24h"

Write-Host "Docker disk usage:" -ForegroundColor Cyan
& docker system df

Write-Host "Done. Volumes were preserved." -ForegroundColor Green
