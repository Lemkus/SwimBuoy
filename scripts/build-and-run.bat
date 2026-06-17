@echo off
setlocal
cd /d "%~dp0.."
call "%~dp0setup-build-link.bat"
if errorlevel 1 exit /b 1

echo [1/4] SDK on X:...
call "%~dp0..\connect-iq\setup-sdk-path.bat"
if errorlevel 1 exit /b 1

echo [2/4] Build fr955...
call X:\bin\monkeyc.bat -f connect-iq\monkey.jungle -o connect-iq\bin\SB_Osinova2.prg -y connect-iq\developer_key.der -d fr955 -w
if errorlevel 1 exit /b 1

if not exist C:\Temp mkdir C:\Temp
copy /Y connect-iq\bin\SB_Osinova2.prg C:\Temp\SB_Osinova2.prg >nul

tasklist /FI "IMAGENAME eq simulator.exe" 2>nul | find /I simulator.exe >nul
if errorlevel 1 (
    echo [3/4] Start simulator...
    start "CIQ Simulator" /D X:\bin X:\bin\simulator.exe
    timeout /t 6 /nobreak >nul
) else (
    echo [3/4] Simulator already running.
)

echo [4/4] Deploy to fr955 (may take 1-2 min)...
call X:\bin\monkeydo.bat C:\Temp\SB_Osinova2.prg fr955
if errorlevel 1 exit /b 1

echo.
echo Done. In simulator: SB_Osinova2 app -^> Activity Data -^> Play
exit /b 0
