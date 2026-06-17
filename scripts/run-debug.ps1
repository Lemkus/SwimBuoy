# Сборка SwimBuoy и запуск в Connect IQ Simulator (fr955)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Set-Location $root
cmd /c "`"$PSScriptRoot\setup-build-link.bat`"" | Out-Null
& "$root\connect-iq\setup-sdk-path.bat" | Out-Null

$prgOut = "$root\connect-iq\bin\SwimBuoy.prg"
$prgTemp = "C:\Temp\SwimBuoy.prg"

Write-Host "Building..."
& "X:\bin\monkeyc.bat" `
    -f "$root\connect-iq\monkey.jungle" `
    -o $prgOut `
    -y "$root\connect-iq\developer_key.der" `
    -d fr955 `
    -w
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

New-Item -ItemType Directory -Force -Path "C:\Temp" | Out-Null
Copy-Item $prgOut $prgTemp -Force

$sim = Get-Process -Name "simulator" -ErrorAction SilentlyContinue
if (-not $sim) {
    Write-Host "Starting CIQ Simulator..."
    Start-Process -FilePath "X:\bin\simulator.exe" -WorkingDirectory "X:\bin"
    Start-Sleep -Seconds 6
}

Write-Host "Deploying to fr955..."
& "X:\bin\monkeydo.bat" $prgTemp fr955
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "OK. In simulator:"
Write-Host "  1. Open app SwimBuoy"
Write-Host "  2. Settings -> Set Position: 60.1200133, 30.2590315 (P1)"
Write-Host "  3. Simulation -> Activity Data -> FIT/GPX -> Load C:\Temp\field_walk.tcx -> Play"
Write-Host ""
Write-Host "Or in Cursor (SwimBuoy folder): F5 = Run App (fr955)"
