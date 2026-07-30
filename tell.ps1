# Tell launcher for Windows (PowerShell).

Push-Location "$PSScriptRoot"
try {
    if (Test-Path ".venv\Scripts\python.exe") {
        & ".venv\Scripts\python.exe" -m ai_terminal @args
        exit $LASTEXITCODE
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        python -m ai_terminal @args
        exit $LASTEXITCODE
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        py -3 -m ai_terminal @args
        exit $LASTEXITCODE
    }
    Write-Error "Python not found. Install Python 3.10+ and add it to PATH."
    exit 1
} finally {
    Pop-Location
}
