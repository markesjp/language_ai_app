param(
    [switch] $Detached,
    [switch] $Attached,
    [switch] $SkipPrometheus,
    [switch] $NoInstall,
    [switch] $NoBrowser
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
$composeArgs = @("compose", "up")
if ($Detached -or -not $Attached) {
    $composeArgs += "-d"
}
$composeArgs += $services

Write-Host "Starting development infrastructure..." -ForegroundColor Cyan
Write-Host "Services: $($services -join ', ')" -ForegroundColor Yellow
& docker @composeArgs

Write-Host "Waiting for infrastructure..." -ForegroundColor Cyan
Wait-ForTcp -HostName "localhost" -Port 5432 -Name "Postgres" -TimeoutSeconds 120 | Out-Null
Wait-ForTcp -HostName "localhost" -Port 6379 -Name "Redis" -TimeoutSeconds 90 | Out-Null

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
Start-Process powershell.exe -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-File", $backendDevScript)

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
