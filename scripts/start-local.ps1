$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$backendRoot = Join-Path $projectRoot 'backend'
$frontendRoot = Join-Path $projectRoot 'frontend'
$logRoot = Join-Path $projectRoot '.tools'
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null

function Test-Endpoint([string]$Url) {
    try { return (Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3).StatusCode -eq 200 }
    catch { return $false }
}

function Wait-Endpoint([string]$Url) {
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        if (Test-Endpoint $Url) { return }
        Start-Sleep -Seconds 1
    }
    throw "Service did not become ready: $Url. Check logs in $logRoot."
}

$pgctl = Join-Path $logRoot 'postgres\pgsql\bin\pg_ctl.exe'
if (Test-Path $pgctl) {
    & $pgctl -D (Join-Path $logRoot 'pgdata') status *> $null
    if ($LASTEXITCODE -ne 0) {
        & $pgctl -D (Join-Path $logRoot 'pgdata') -l (Join-Path $logRoot 'postgres.log') -o '-h 127.0.0.1 -p 55432' start
        if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL failed to start. Check .tools/postgres.log.' }
    }
} else {
    Write-Host 'Using your configured PostgreSQL service. Start it before running this script.'
}

$python = Join-Path $backendRoot '.venv\Scripts\python.exe'
if (!(Test-Path $python)) { throw 'Create the backend virtual environment using README.md first.' }

Push-Location $backendRoot
try {
    & $python -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw 'Migration failed. Check PostgreSQL and backend/.env.' }
} finally { Pop-Location }

if (!(Test-Endpoint 'http://127.0.0.1:8000/api/v1/health')) {
    Start-Process -FilePath $python -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--reload', '--host', '127.0.0.1', '--port', '8000') -WorkingDirectory $backendRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logRoot 'backend-dev.log') -RedirectStandardError (Join-Path $logRoot 'backend-dev-error.log') | Out-Null
}
Wait-Endpoint 'http://127.0.0.1:8000/api/v1/ready'

if (!(Test-Endpoint 'http://127.0.0.1:3000')) {
    $nodeCommand = Get-Command node -ErrorAction SilentlyContinue
    if (!$nodeCommand) { throw 'Install Node.js and reopen your terminal first.' }
    $next = Join-Path $frontendRoot 'node_modules\next\dist\bin\next'
    if (!(Test-Path $next)) { throw 'Run npm ci in frontend first.' }
    Start-Process -FilePath $nodeCommand.Source -ArgumentList @(('"' + $next + '"'), 'dev', '--hostname', '127.0.0.1', '--port', '3000') -WorkingDirectory $frontendRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logRoot 'frontend-dev.log') -RedirectStandardError (Join-Path $logRoot 'frontend-dev-error.log') | Out-Null
}
Wait-Endpoint 'http://127.0.0.1:3000'
Write-Host 'Application ready: http://127.0.0.1:3000'
Write-Host 'PostgreSQL, backend and frontend must all stay running while you preview the site.'
