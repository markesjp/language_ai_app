param(
    [switch] $Detached,
    [switch] $OllamaDocker
)

$ErrorActionPreference = "Stop"

$composeArgs = @("compose")
if ($OllamaDocker) {
    $composeArgs += @("-f", "docker-compose.yml", "-f", "docker-compose.ollama.yml", "--profile", "ollama-gpu")
}
$composeArgs += @("up", "--build")
if ($Detached) {
    $composeArgs += "-d"
}

Write-Host "Starting LinguaFlow AI..." -ForegroundColor Cyan
if ($OllamaDocker) {
    Write-Host "Using Ollama in Docker with GPU profile." -ForegroundColor Yellow
} else {
    Write-Host "Using Ollama from Windows host at host.docker.internal:11434." -ForegroundColor Yellow
}

& docker @composeArgs
