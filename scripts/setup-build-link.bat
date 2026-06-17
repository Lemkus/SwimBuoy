@echo off
setlocal
cd /d "%~dp0.."

if exist "bin\" (
    exit /b 0
)

if not exist "connect-iq\bin\" mkdir "connect-iq\bin"
mklink /J "bin" "connect-iq\bin" >nul
if errorlevel 1 (
    echo Failed to create bin junction. Run this script from an elevated cmd once, or create manually:
    echo   mklink /J bin connect-iq\bin
    exit /b 1
)
exit /b 0
