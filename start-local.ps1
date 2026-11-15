$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Frontend = Join-Path $Root 'frontend'
$Backend = Join-Path $Root 'backend'
$LocalDir = Join-Path $Root '.local'
$LogDir = Join-Path $LocalDir 'logs'
$Venv = Join-Path $Root '.venv-local'
$BackendPort = 8000
$FrontendPort = 3000
$BackendUrl = "http://127.0.0.1:$BackendPort"
$FrontendUrl = "http://localhost:$FrontendPort"
$StartedProcesses = [System.Collections.Generic.List[int]]::new()
$BackendProcess = $null
$FrontendProcess = $null

function Stop-OwnedProcessTree([int]$ProcessId) {
    if (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue) {
        & taskkill.exe /PID $ProcessId /T /F 2>$null | Out-Null
    }
}

function Test-ListeningPort([int]$Port) {
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $result = $client.BeginConnect('127.0.0.1', $Port, $null, $null)
        if (-not $result.AsyncWaitHandle.WaitOne(300)) { return $false }
        $client.EndConnect($result)
        return $true
    }
    catch { return $false }
    finally { $client.Dispose() }
}

function Get-HttpResponse([string]$Url) {
    try { return Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop }
    catch { return $null }
}

function Get-PythonVersion([string]$Executable) {
    try {
        $versionText = & $Executable -c 'import sys; print(str(sys.version_info[0])+chr(46)+str(sys.version_info[1]))' 2>$null
        if ($LASTEXITCODE -eq 0 -and $versionText -match '^\d+\.\d+$') { return $versionText }
    }
    catch { }
    return $null
}

function Find-CompatiblePython {
    $candidates = [System.Collections.Generic.List[string]]::new()
    $pythonOnPath = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($pythonOnPath) { $candidates.Add($pythonOnPath.Source) }

    $pyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        $installed = & $pyLauncher.Source -0p 2>$null
        foreach ($line in $installed) {
            if ($line -match '(?i)([A-Z]:\\.*?python(?:\.exe)?)\s*$') {
                $candidate = $Matches[1]
                if (Test-Path -LiteralPath $candidate) { $candidates.Add($candidate) }
            }
        }
    }

    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        $version = Get-PythonVersion $candidate
        if ($version -and [version]$version -ge [version]'3.12' -and [version]$version -lt [version]'3.16') {
            return @{ Path = $candidate; Version = $version }
        }
    }
    throw 'Python 3.12, 3.13, 3.14, or 3.15 is required. Install a supported 64-bit Python and rerun .\start-local.ps1.'
}

function Ensure-BackendEnvironment($Python) {
    $venvPython = Join-Path $Venv 'Scripts\python.exe'
    if (-not (Test-Path $venvPython)) {
        Write-Host "Creating local Python environment with Python $($Python.Version)..."
        & $Python.Path -m venv $Venv
        if ($LASTEXITCODE -ne 0) { throw 'Python virtual environment creation failed.' }
    }
    $localVersion = Get-PythonVersion $venvPython
    if (-not $localVersion -or [version]$localVersion -lt [version]'3.12' -or [version]$localVersion -ge [version]'3.16') {
        throw "The existing .venv-local uses unsupported Python $localVersion. Remove or rename .venv-local and rerun the launcher."
    }

    $requirements = Join-Path $Backend 'requirements-dev.txt'
    $hashFile = Join-Path $Venv '.firelytics-requirements-sha256'
    $requirementsHash = (Get-FileHash -LiteralPath $requirements -Algorithm SHA256).Hash
    $savedHash = if (Test-Path $hashFile) { (Get-Content -Raw $hashFile).Trim() } else { '' }
    if ($savedHash -ne $requirementsHash) {
        Write-Host 'Installing or updating backend dependencies...'
        & $venvPython -m pip install -r $requirements | Out-Host
        if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed. Check the backend requirements and Python installation, then rerun the launcher.' }
        Set-Content -LiteralPath $hashFile -Value $requirementsHash -NoNewline -Encoding ascii
    }
    return $venvPython
}

function Ensure-FrontendDependencies([string]$NodeDirectory) {
    $nextPackage = Join-Path $Frontend 'node_modules\next\package.json'
    $lockFile = Join-Path $Frontend 'package-lock.json'
    $frontendHash = (Get-FileHash -LiteralPath $lockFile -Algorithm SHA256).Hash
    $hashFile = Join-Path $LocalDir 'frontend-lock-sha256'
    $savedHash = if (Test-Path $hashFile) { (Get-Content -Raw $hashFile).Trim() } else { '' }
    if ((Test-Path $nextPackage) -and $savedHash -eq $frontendHash) { return }
    $npm = Join-Path $NodeDirectory 'npm.cmd'
    if (-not (Test-Path $npm)) {
        $npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
        if ($npmCommand) { $npm = $npmCommand.Source } else { throw 'Frontend dependencies are missing and npm.cmd was not found beside Node.js. Install Node.js 22 or restore the bundled .tools runtime.' }
    }
    Write-Host 'Installing frontend dependencies from frontend/package-lock.json...'
    & $npm ci --prefix $Frontend
    if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed. Check network access and frontend/package-lock.json, then rerun the launcher.' }
    Set-Content -LiteralPath $hashFile -Value $frontendHash -NoNewline -Encoding ascii
}

function Wait-ForHttp([string]$Url, [System.Diagnostics.Process]$Process, [int]$TimeoutSeconds, [string]$ServiceName) {
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        if ($Process -and $Process.HasExited) {
            throw "$ServiceName exited during startup (exit code $($Process.ExitCode)). See logs in $LogDir."
        }
        $response = Get-HttpResponse $Url
        if ($response -and $response.StatusCode -ge 200 -and $response.StatusCode -lt 500) { return $response }
        Start-Sleep -Milliseconds 500
    }
    throw "$ServiceName did not become ready within $TimeoutSeconds seconds. See logs in $LogDir."
}

try {
    foreach ($folder in @($Frontend, $Backend)) {
        if (-not (Test-Path -LiteralPath $folder)) { throw "Required project folder is missing: $folder" }
    }

    $python = Find-CompatiblePython
    Write-Host "Python $($python.Version): $($python.Path)"

    $portableNode = Join-Path $Root '.tools\node-v22.23.5-win-x64'
    $nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
    $nodePath = if ($nodeCommand) { $nodeCommand.Source } else { Join-Path $portableNode 'node.exe' }
    if (-not (Test-Path $nodePath)) { throw 'Node.js 22 is required. Install Node.js 22 or restore .tools\node-v22.23.5-win-x64.' }
    $nodeVersion = (& $nodePath --version).Trim().TrimStart('v')
    if ($LASTEXITCODE -ne 0 -or $nodeVersion -notmatch '^22\.') { throw "Node.js 22 is required by frontend/package.json; found $nodeVersion at $nodePath." }
    $nodeDirectory = Split-Path -Parent $nodePath
    $env:PATH = "$nodeDirectory;$env:PATH"
    Write-Host "Node.js ${nodeVersion}: $nodePath"

    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
    $backendPython = Ensure-BackendEnvironment $python
    Ensure-FrontendDependencies $nodeDirectory

    $backendAlreadyReady = $false
    if (Test-ListeningPort $BackendPort) {
        $backendHealth = Get-HttpResponse "$BackendUrl/health"
        if (-not $backendHealth -or $backendHealth.StatusCode -ne 200) { throw "Port $BackendPort is occupied by a service that does not answer the FIRELYTICS health check. Stop the service using that port or update start-local.ps1." }
        $backendAlreadyReady = $true
        Write-Host 'A healthy backend is already running; reusing it.'
    }
    else {
        $outLog = Join-Path $LogDir 'backend-out.log'
        $errorLog = Join-Path $LogDir 'backend-error.log'
        $BackendProcess = Start-Process -FilePath $backendPython -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port',"$BackendPort") -WorkingDirectory $Backend -PassThru -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errorLog
        $StartedProcesses.Add($BackendProcess.Id)
        [void](Wait-ForHttp "$BackendUrl/health" $BackendProcess 60 'FastAPI backend')
        Write-Host 'FastAPI backend is healthy.'
    }

    $frontendAlreadyReady = $false
    if (Test-ListeningPort $FrontendPort) {
        $frontendResponse = Get-HttpResponse $FrontendUrl
        if (-not $frontendResponse -or $frontendResponse.StatusCode -ne 200) { throw "Port $FrontendPort is occupied by a service that does not serve the FIRELYTICS frontend. Stop the service using that port or update start-local.ps1." }
        $frontendAlreadyReady = $true
        Write-Host 'A frontend is already running; checking its API proxy.'
    }
    else {
        $outLog = Join-Path $LogDir 'frontend-out.log'
        $errorLog = Join-Path $LogDir 'frontend-error.log'
        $nextScript = Join-Path $Frontend 'scripts\next.mjs'
        $previousBackendUrl = $env:BACKEND_URL
        $previousTelemetry = $env:NEXT_TELEMETRY_DISABLED
        $env:BACKEND_URL = $BackendUrl
        $env:NEXT_TELEMETRY_DISABLED = '1'
        try {
            $FrontendProcess = Start-Process -FilePath $nodePath -ArgumentList @($nextScript,'dev','--hostname','127.0.0.1','--port',"$FrontendPort") -WorkingDirectory $Frontend -PassThru -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errorLog
        }
        finally {
            if ($null -eq $previousBackendUrl) { Remove-Item Env:\BACKEND_URL -ErrorAction SilentlyContinue } else { $env:BACKEND_URL = $previousBackendUrl }
            if ($null -eq $previousTelemetry) { Remove-Item Env:\NEXT_TELEMETRY_DISABLED -ErrorAction SilentlyContinue } else { $env:NEXT_TELEMETRY_DISABLED = $previousTelemetry }
        }
        $StartedProcesses.Add($FrontendProcess.Id)
        [void](Wait-ForHttp $FrontendUrl $FrontendProcess 120 'Next.js frontend')
        Write-Host 'Next.js frontend is responding.'
    }

    $proxyResponse = Get-HttpResponse "$FrontendUrl/api/backend/health"
    if (-not $proxyResponse -or $proxyResponse.StatusCode -ne 200) {
        throw 'The frontend API proxy could not reach the backend health route. See frontend-error.log and backend-error.log in .local\logs.'
    }

    Write-Host ''
    Write-Host 'FIRELYTICS AI is ready.' -ForegroundColor Green
    Write-Host "Frontend: $FrontendUrl"
    Write-Host "Backend:  $BackendUrl"
    Write-Host "API docs: $BackendUrl/docs"
    Write-Host "Logs:     $LogDir"
    Start-Process $FrontendUrl
    Write-Host 'Press Ctrl+C to stop services started by this launcher.'

    while ($true) {
        foreach ($service in @(@{ Name = 'FastAPI'; Process = $BackendProcess }, @{ Name = 'Next.js'; Process = $FrontendProcess })) {
            if ($service.Process -and $service.Process.HasExited) {
                throw "$($service.Name) stopped (exit code $($service.Process.ExitCode)). See logs in $LogDir."
            }
        }
        Start-Sleep -Seconds 2
    }
}
catch {
    Write-Error $_.Exception.Message
    if ($StartedProcesses.Count -gt 0) { Write-Host 'Stopping service processes started during this launch...' }
    foreach ($processId in $StartedProcesses) { Stop-OwnedProcessTree $processId }
    exit 1
}
finally {
    foreach ($processId in $StartedProcesses) { Stop-OwnedProcessTree $processId }
}
