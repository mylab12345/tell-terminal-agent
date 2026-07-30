@echo off
REM AITA launcher for Windows (cmd.exe).
REM Runs the AI terminal agent from the project folder.
setlocal
cd /d "%~dp0"

REM Prefer a local virtualenv if present, otherwise try system python or the Python launcher.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m ai_terminal %*
) else (
    where python >nul 2>&1
    if %ERRORLEVEL%==0 (
        python -m ai_terminal %*
    ) else (
        where py >nul 2>&1
        if %ERRORLEVEL%==0 (
            py -3 -m ai_terminal %*
        ) else (
            echo Python not found on PATH and the Python launcher (py) is not available.
            echo Install Python, enable "Add Python to PATH", or install the Python launcher.
            exit /b 1
        )
    )
)

endlocal