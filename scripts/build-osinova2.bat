@echo off
setlocal
cd /d "%~dp0.."
call "%~dp0setup-build-link.bat"
if errorlevel 1 exit /b 1

echo [1/2] SDK on X:...
call "%~dp0..\connect-iq\setup-sdk-path.bat"
if errorlevel 1 exit /b 1

echo [2/2] Build fr955 SB_Osinova2...
call X:\bin\monkeyc.bat -f connect-iq\monkey.jungle -o connect-iq\bin\SB_Osinova2.prg -y connect-iq\developer_key.der -d fr955 -w
if errorlevel 1 exit /b 1

if not exist C:\Temp mkdir C:\Temp
copy /Y connect-iq\bin\SB_Osinova2.prg C:\Temp\SB_Osinova2.prg >nul
echo BUILD OK: connect-iq\bin\SB_Osinova2.prg
exit /b 0
