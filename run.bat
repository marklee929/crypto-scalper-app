@echo off
setlocal

cd /d "%~dp0"

if "%~1"=="" (
    set RUN_ARGS=--mode demo --demo-profile pump --ticks 240
) else (
    set RUN_ARGS=%*
)

echo [BAT] Starting Heart Beat Coin Scalper...
echo [BAT] Working directory: %CD%
echo [BAT] Safe default: demo pump log. Use --live only for live runtime.
echo [BAT] Command: python "%~dp0run.py" %RUN_ARGS%
echo.

python "%~dp0run.py" %RUN_ARGS%
set EXIT_CODE=%ERRORLEVEL%

echo.
echo [BAT] Exited with code %EXIT_CODE%.
if not "%EXIT_CODE%"=="0" (
    echo [BAT] Press any key to close this window.
    pause >nul
)

exit /b %EXIT_CODE%
