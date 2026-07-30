# PowerShell launcher for the AI terminal agent.
# Run this from the project folder with .\tell.ps1 or add the folder to PATH.

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

    Write-Error "Python not found on PATH and the Python launcher (py) is not available."
    Write-Error "Install Python, enable 'Add Python to PATH', or install the Python launcher."
    exit 1
} finally {
    Pop-Location
}
