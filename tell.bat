@echo off
REM AITA/TELL launcher for Windows (cmd.exe).
REM Runs the AI terminal agent from the project folder.
setlocal
cd /d "%~dp0"

REM Prefer a local virtualenv if present.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m ai_terminal %*
    endlocal
    exit /b %ERRORLEVEL%
)

REM Otherwise prefer a system python executable.
where python >nul 2>&1
if errorlevel 0 if not errorlevel 1 (
    python -m ai_terminal %*
    endlocal
    exit /b %ERRORLEVEL%
)

REM Fallback to the Python launcher.
where py >nul 2>&1
if errorlevel 0 if not errorlevel 1 (
    py -3 -m ai_terminal %*
    endlocal
    exit /b %ERRORLEVEL%
)

echo Python not found on PATH and the Python launcher (py) is not available.
echo Install Python, enable "Add Python to PATH", or install the Python launcher.
endlocal
exit /b 1
