$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================"
Write-Host " ESM Trade System - Windows Server Build"
Write-Host "========================================"
Write-Host ""

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Set-Location $ProjectRoot


Write-Host "1. Running Python tests..."
python -m pytest

if ($LASTEXITCODE -ne 0) {
    throw "Python tests failed."
}


Write-Host ""
Write-Host "2. Building frontend..."

Set-Location "$ProjectRoot\frontend"

npm run build

if ($LASTEXITCODE -ne 0) {
    throw "Frontend build failed."
}


if (-not (Test-Path "$ProjectRoot\frontend\dist\index.html")) {
    throw "frontend\dist\index.html was not created."
}


Set-Location $ProjectRoot


Write-Host ""
Write-Host "3. Checking PyInstaller..."

python -c "import PyInstaller"

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller is not installed. Run: pip install pyinstaller"
}


Write-Host ""
Write-Host "4. Checking T-Invest SDK..."

python -c "import t_tech.invest; import t_tech.invest.certs; print('T-Invest SDK OK')"

if ($LASTEXITCODE -ne 0) {
    throw "T-Invest SDK is not installed correctly."
}


Write-Host ""
Write-Host "5. Checking SDK location..."

python -c "import t_tech.invest; print(t_tech.invest.__file__)"

if ($LASTEXITCODE -ne 0) {
    throw "Cannot locate t_tech.invest package."
}


Write-Host ""
Write-Host "6. Cleaning previous build..."

if (Test-Path "$ProjectRoot\build") {
    Remove-Item `
        "$ProjectRoot\build" `
        -Recurse `
        -Force
}

if (Test-Path "$ProjectRoot\dist\ESMTradeSystem.exe") {
    Remove-Item `
        "$ProjectRoot\dist\ESMTradeSystem.exe" `
        -Force
}


Write-Host ""
Write-Host "7. Building ESMTradeSystem.exe..."

python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --console `
    --name "ESMTradeSystem" `
    --paths "$ProjectRoot\app" `
    --add-data "$ProjectRoot\frontend\dist;frontend\dist" `
    --collect-all "t_tech.invest" `
    --collect-all "certifi" `
    --hidden-import "t_tech.invest.certs" `
    --hidden-import "grpc" `
    --hidden-import "grpc.aio" `
    "$ProjectRoot\run_server.py"

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}


$ExePath = "$ProjectRoot\dist\ESMTradeSystem.exe"

if (-not (Test-Path $ExePath)) {
    throw "ESMTradeSystem.exe was not created."
}


Write-Host ""
Write-Host "8. Build file information..."

$ExeItem = Get-Item $ExePath

Write-Host "Path:"
Write-Host $ExeItem.FullName

Write-Host ""
Write-Host "Size:"
Write-Host "$([Math]::Round($ExeItem.Length / 1MB, 2)) MB"


Write-Host ""
Write-Host "========================================"
Write-Host " BUILD SUCCESS"
Write-Host "========================================"
Write-Host ""
Write-Host "Executable:"
Write-Host $ExePath
Write-Host ""
Write-Host "The build includes:"
Write-Host " - Python backend"
Write-Host " - React frontend"
Write-Host " - t_tech.invest SDK"
Write-Host " - t_tech.invest.certs"
Write-Host " - certifi certificates"
Write-Host " - gRPC modules"
Write-Host ""
