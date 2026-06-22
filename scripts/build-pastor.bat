@echo off
setlocal
cd /d "%~dp0.."
if "%~1"=="" (
    echo Usage: build-pastor.bat ^<output_name^>
    echo   e.g. build-pastor.bat SB_Pastor_before
    exit /b 1
)
set OUT=%~1

call "%~dp0setup-build-link.bat"
if errorlevel 1 exit /b 1

call "%~dp0..\connect-iq\setup-sdk-path.bat"
if errorlevel 1 exit /b 1

echo Building fr955 %OUT%...
call X:\bin\monkeyc.bat -f connect-iq\monkey.jungle -o connect-iq\bin\%OUT%.prg -y connect-iq\developer_key.der -d fr955 -w
if errorlevel 1 exit /b 1

if not exist C:\Temp mkdir C:\Temp
copy /Y connect-iq\bin\%OUT%.prg C:\Temp\%OUT%.prg >nul
echo BUILD OK: connect-iq\bin\%OUT%.prg
exit /b 0
