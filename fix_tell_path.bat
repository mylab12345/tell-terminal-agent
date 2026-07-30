@echo off
setlocal enabledelayedexpansion
for %%I in ("%~dp0..") do set "ROOT=%%~fI"
set "CURPATH="
for /f "tokens=2,*" %%A in ('reg query HKCU\Environment /v Path 2^>nul ^| findstr /R /C:"Path"') do (
    set "CURPATH=%%B"
)
if "%CURPATH%"=="" (
    reg add HKCU\Environment /v Path /t REG_EXPAND_SZ /d "%ROOT%" /f
    echo Added %ROOT% to user PATH.
) else (
    echo Current user PATH: %CURPATH%
    echo %CURPATH% | find /I "%ROOT%" >nul
    if errorlevel 1 (
        reg add HKCU\Environment /v Path /t REG_EXPAND_SZ /d "%CURPATH%;%ROOT%" /f
        echo Added %ROOT% to user PATH.
    ) else (
        echo Repo root already in user PATH.
    )
)
echo Done. Restart your terminal for changes to take effect.
endlocal
