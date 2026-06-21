$ErrorActionPreference = "Continue"

Write-Host "Compose services:" -ForegroundColor Cyan
docker compose ps

Write-Host "`nDocker disk usage:" -ForegroundColor Cyan
docker system df

Write-Host "`nGPU status:" -ForegroundColor Cyan
nvidia-smi

Write-Host "`nOllama host endpoint:" -ForegroundColor Cyan
try {
    Invoke-RestMethod http://localhost:11434/api/tags -TimeoutSec 5 | ConvertTo-Json -Depth 5
} catch {
    Write-Host "Ollama is not reachable at http://localhost:11434" -ForegroundColor Yellow
    Write-Host $_.Exception.Message -ForegroundColor Yellow
}
