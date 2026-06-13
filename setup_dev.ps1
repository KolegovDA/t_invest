Write-Host "=== T-Invest Bot: dev setup ==="

if (-Not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    py -m venv .venv
}

Write-Host "Activating virtual environment..."
& ".\.venv\Scripts\Activate.ps1"

Write-Host "Upgrading pip..."
python -m pip install --upgrade pip

Write-Host "Installing dependencies..."
pip install `
    pydantic `
    sqlalchemy `
    pytest `
    ruff `
    mypy `
    python-dotenv `
    pyyaml `
    pandas `
    numpy `
    matplotlib `
    tinkoff-investments

Write-Host "Creating project folders..."

New-Item -ItemType Directory -Force -Path "docs" | Out-Null
New-Item -ItemType Directory -Force -Path "t_invest_bot\app\domain" | Out-Null
New-Item -ItemType Directory -Force -Path "t_invest_bot\app\strategy" | Out-Null
New-Item -ItemType Directory -Force -Path "t_invest_bot\app\backtest" | Out-Null
New-Item -ItemType Directory -Force -Path "t_invest_bot\app\application" | Out-Null
New-Item -ItemType Directory -Force -Path "t_invest_bot\app\infrastructure" | Out-Null
New-Item -ItemType Directory -Force -Path "t_invest_bot\app\analytics" | Out-Null
New-Item -ItemType Directory -Force -Path "t_invest_bot\app\config" | Out-Null
New-Item -ItemType Directory -Force -Path "t_invest_bot\tests" | Out-Null

Write-Host "Creating empty __init__.py files..."

$initFiles = @(
    "t_invest_bot\app\__init__.py",
    "t_invest_bot\app\domain\__init__.py",
    "t_invest_bot\app\strategy\__init__.py",
    "t_invest_bot\app\backtest\__init__.py",
    "t_invest_bot\app\application\__init__.py",
    "t_invest_bot\app\infrastructure\__init__.py",
    "t_invest_bot\app\analytics\__init__.py",
    "t_invest_bot\app\config\__init__.py",
    "t_invest_bot\tests\__init__.py"
)

foreach ($file in $initFiles) {
    if (-Not (Test-Path $file)) {
        New-Item -ItemType File -Path $file | Out-Null
    }
}

Write-Host "Setup complete."
Write-Host "To activate later, run:"
Write-Host ".\.venv\Scripts\Activate.ps1"