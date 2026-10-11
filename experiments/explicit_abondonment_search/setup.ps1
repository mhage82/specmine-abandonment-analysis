param(
    [string]$PythonCommand = "python"
)

$ErrorActionPreference = "Stop"
$requirementsPath = Join-Path $PSScriptRoot "requirements.txt"
$venvPath = Join-Path $PSScriptRoot ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"

if (-not (Test-Path -LiteralPath $requirementsPath)) {
    throw "Requirements file not found: $requirementsPath"
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host "Creating virtual environment: $venvPath"
    & $PythonCommand -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        throw "Virtual environment creation failed. Ensure Python is installed."
    }
}

Write-Host "Installing requirements..."
& $venvPython -m pip install -r $requirementsPath
if ($LASTEXITCODE -ne 0) {
    throw "Dependency installation failed."
}

Write-Host "Setup complete. Run the experiment with:"
Write-Host "& '$venvPython' '$(Join-Path $PSScriptRoot 'search.py')'"
