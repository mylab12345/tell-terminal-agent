@echo off
REM Tell launcher for Windows (cmd.exe).
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m ai_terminal %*
    exit /b %ERRORLEVEL%
)

where python >nul 2>&1 && (
    python -m ai_terminal %*
    exit /b %ERRORLEVEL%
)

where py >nul 2>&1 && (
    py -3 -m ai_terminal %*
    exit /b %ERRORLEVEL%
)

echo Python not found. Install Python 3.10+ and add it to PATH.
endlocal
exit /b 1
