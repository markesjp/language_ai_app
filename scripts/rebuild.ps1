param(
    [switch] $NoCache
)

$ErrorActionPreference = "Stop"

$services = @("frontend", "backend", "worker")
$buildArgs = @("compose", "build")
if ($NoCache) {
    $buildArgs += "--no-cache"
}
$buildArgs += $services

Write-Host "Building app services..." -ForegroundColor Cyan
& docker @buildArgs

Write-Host "Recreating app containers..." -ForegroundColor Cyan
& docker compose up -d --force-recreate frontend backend worker nginx

Write-Host "Cleaning dangling images and safe build cache only..." -ForegroundColor Cyan
& docker image prune -f
& docker builder prune -f --filter "until=24h"

Write-Host "Docker disk usage after cleanup:" -ForegroundColor Cyan
& docker system df
