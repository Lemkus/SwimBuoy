@echo off
setlocal
set "SDK=%APPDATA%\Garmin\ConnectIQ\Sdks\connectiq-sdk-win-9.1.0-2026-03-09-6a872a80b"
if not exist "%SDK%\bin\monkeyc.bat" (
    echo Connect IQ SDK not found: %SDK%
    exit /b 1
)
subst X: /D >nul 2>&1
subst X: "%SDK%"
if errorlevel 1 (
    echo Failed to map X: to SDK
    exit /b 1
)
echo SDK mapped to X:\
exit /b 0
