param(
    [switch] $Detached,
    [switch] $Attached,
    [switch] $SkipPrometheus,
    [switch] $NoInstall,
    [switch] $NoBrowser,
    [switch] $NoWarmOllama
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"
$backendVenvPython = Join-Path $backendDir ".venv\Scripts\python.exe"
$frontendNodeModules = Join-Path $frontendDir "node_modules"
$backendDevScript = Join-Path $PSScriptRoot "dev-backend.ps1"
$frontendDevScript = Join-Path $PSScriptRoot "dev-frontend.ps1"

function Wait-ForUrl {
    param(
        [string] $Url,
        [string] $Name,
        [int] $TimeoutSeconds = 90
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 | Out-Null
            Write-Host "$Name is ready: $Url" -ForegroundColor Green
            return $true
        } catch {
            Start-Sleep -Seconds 2
        }
    }

    Write-Host "$Name did not respond within ${TimeoutSeconds}s: $Url" -ForegroundColor Yellow
    return $false
}

function Wait-ForTcp {
    param(
        [string] $HostName,
        [int] $Port,
        [string] $Name,
        [int] $TimeoutSeconds = 90
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $client = [System.Net.Sockets.TcpClient]::new()
        try {
            $connect = $client.BeginConnect($HostName, $Port, $null, $null)
            if ($connect.AsyncWaitHandle.WaitOne(1000)) {
                $client.EndConnect($connect)
                Write-Host "$Name is reachable: ${HostName}:${Port}" -ForegroundColor Green
                return $true
            }
        } catch {
        } finally {
            $client.Close()
        }
        Start-Sleep -Seconds 2
    }

    Write-Host "$Name did not become reachable within ${TimeoutSeconds}s: ${HostName}:${Port}" -ForegroundColor Yellow
    return $false
}

$services = @("postgres", "pgbouncer", "redis")
if (-not $SkipPrometheus) {
    $services += "prometheus"
}

Write-Host "Stopping Docker app containers that conflict with local hot reload..." -ForegroundColor Cyan
& docker compose stop backend frontend worker nginx 2>$null | Out-Null

$composeArgs = @("compose", "up")
if ($Detached -or -not $Attached) {
    $composeArgs += "-d"
}
$composeArgs += $services

Write-Host "Starting development infrastructure..." -ForegroundColor Cyan
Write-Host "Services: $($services -join ', ')" -ForegroundColor Yellow
& docker @composeArgs

Write-Host "Waiting for infrastructure..." -ForegroundColor Cyan
$postgresPort = (& docker compose port postgres 5432).Split(":")[-1].Trim()
if (-not $postgresPort) {
    $postgresPort = "5432"
}
Write-Host "Postgres host port: $postgresPort" -ForegroundColor DarkGray
Wait-ForTcp -HostName "localhost" -Port ([int] $postgresPort) -Name "Postgres" -TimeoutSeconds 120 | Out-Null
Wait-ForTcp -HostName "localhost" -Port 6379 -Name "Redis" -TimeoutSeconds 90 | Out-Null

# Ensure Ollama is running with CUDA (not Vulkan which picks Intel iGPU and crashes)
$ollamaRunning = $false
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:11434/" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    $ollamaRunning = $true
    Write-Host "Ollama already running." -ForegroundColor Green
} catch {
    $ollamaRunning = $false
}
if (-not $ollamaRunning) {
    Write-Host "Starting Ollama (CUDA mode)..." -ForegroundColor Cyan
    $env:OLLAMA_VULKAN = "false"
    $ollamaExe = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
    if (Test-Path $ollamaExe) {
        Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
        Wait-ForUrl -Url "http://localhost:11434/" -Name "Ollama" -TimeoutSeconds 30 | Out-Null
    } else {
        Write-Host "Ollama not found at $ollamaExe. Install from https://ollama.com" -ForegroundColor Yellow
    }
}

if (-not $NoWarmOllama) {
    Write-Host "Warming Ollama models..." -ForegroundColor Cyan
    try {
        $generateBody = @{
            model = "llama3.2"
            prompt = "ok"
            stream = $false
            keep_alive = "15m"
            options = @{
                num_ctx = 1024
                num_predict = 1
            }
        } | ConvertTo-Json -Depth 5
        Invoke-RestMethod -Uri "http://localhost:11434/api/generate" -Method Post -ContentType "application/json" -Body $generateBody -TimeoutSec 120 | Out-Null

        $embedBody = @{
            model = "nomic-embed-text"
            input = "warmup"
            keep_alive = "15m"
        } | ConvertTo-Json -Depth 5
        Invoke-RestMethod -Uri "http://localhost:11434/api/embed" -Method Post -ContentType "application/json" -Body $embedBody -TimeoutSec 120 | Out-Null
        Write-Host "Ollama models are warm." -ForegroundColor Green
    } catch {
        Write-Host "Could not warm Ollama models: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

if (-not (Test-Path $backendVenvPython)) {
    Write-Host "Creating backend virtual environment..." -ForegroundColor Cyan
    & python -m venv (Join-Path $backendDir ".venv")
}

if (-not $NoInstall) {
    Write-Host "Installing backend dependencies..." -ForegroundColor Cyan
    & $backendVenvPython -m pip install -r (Join-Path $backendDir "requirements.txt")

    if (-not (Test-Path $frontendNodeModules)) {
        Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
        Push-Location $frontendDir
        try {
            npm install
        } finally {
            Pop-Location
        }
    } else {
        Write-Host "Frontend dependencies already installed. Use npm install manually after package changes." -ForegroundColor DarkGray
    }
}

Write-Host "Starting backend hot reload window..." -ForegroundColor Cyan
Start-Process powershell.exe -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-File", $backendDevScript, "-PostgresPort", $postgresPort)

Write-Host "Starting frontend hot reload window..." -ForegroundColor Cyan
Start-Process powershell.exe -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-File", $frontendDevScript)

Write-Host ""
Write-Host "Waiting for local services..." -ForegroundColor Cyan
Wait-ForUrl -Url "http://localhost:8000/api/v1/health" -Name "Backend" -TimeoutSeconds 90 | Out-Null
$frontendReady = Wait-ForUrl -Url "http://localhost:3000" -Name "Frontend" -TimeoutSeconds 120

if ($frontendReady -and -not $NoBrowser) {
    Start-Process "http://localhost:3000"
}

Write-Host ""
Write-Host "Development is ready." -ForegroundColor Green
Write-Host "Web: http://localhost:3000"
Write-Host "API: http://localhost:8000/api/v1/health"
Write-Host "Swagger: http://localhost:8000/docs"
