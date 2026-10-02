$ErrorActionPreference = "Stop"
$Repo = "https://github.com/nadeemmhdm/ai-brain-assistant.git"
$InstallDir = Join-Path $env:LOCALAPPDATA "AI-Brain-Assistant"

function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
}

function Ensure-WingetPackage($Command, $Id) {
    if (Get-Command $Command -ErrorAction SilentlyContinue) { return }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "$Command is required and winget is unavailable. Install $Command, then run this command again."
    }
    Write-Host "[install] Installing $Command..."
    winget install --id $Id -e --accept-package-agreements --accept-source-agreements
    Refresh-Path
}

Write-Host "AI Brain Assistant - automatic installer"
Ensure-WingetPackage "git" "Git.Git"
Ensure-WingetPackage "python" "Python.Python.3.12"
Ensure-WingetPackage "node" "OpenJS.NodeJS.LTS"

if (Test-Path (Join-Path $InstallDir ".git")) {
    Write-Host "[install] Existing AI Brain installation found."
} elseif (Test-Path $InstallDir) {
    throw "Install path already exists but is not an AI Brain git checkout: $InstallDir"
} else {
    Write-Host "[install] Downloading AI Brain..."
    git clone $Repo $InstallDir
}

Set-Location $InstallDir
$Python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Python) {
    $Python = (Get-Command py -ErrorAction SilentlyContinue).Source
    if ($Python) { & $Python -3 scripts\bootstrap.py; exit $LASTEXITCODE }
    throw "Python was installed but is not visible in this terminal yet. Open a new PowerShell and run the installer again."
}
& $Python scripts\bootstrap.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Installed successfully: $InstallDir"
Write-Host "Start AI Brain with: $InstallDir\run.bat"
