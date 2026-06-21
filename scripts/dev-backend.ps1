$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$backendDir = Join-Path $root "backend"
$backendActivate = Join-Path $backendDir ".venv\Scripts\Activate.ps1"
$envFile = Join-Path $root ".env"

if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
            return
        }
        $name, $value = $line.Split("=", 2)
        [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), "Process")
    }
}

$env:DATABASE_URL = "postgresql+asyncpg://language_user:language_pass@localhost:5432/language_ai"
$env:REDIS_URL = "redis://localhost:6379/0"
$env:OLLAMA_BASE_URL = "http://localhost:11434"
[Environment]::SetEnvironmentVariable("CORS_ORIGINS", '["http://localhost","http://localhost:3000"]', "Process")

Set-Location $backendDir
. $backendActivate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
