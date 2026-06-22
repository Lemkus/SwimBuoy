# Full auto-run: Shchuchye route + Kolya GPX playback in CIQ Simulator (Windows GUI automation).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$gpx = "C:\Temp\shuchye_sim.gpx"
$prg = "C:\Temp\SB_Pastor.prg"

Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class NativeWin {
    public const int SW_RESTORE = 9;
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT r);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
}
"@

function Wait-Ms([int]$ms) { Start-Sleep -Milliseconds $ms }

function Focus-Simulator {
    $sim = Get-Process -Name simulator -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $sim) { throw "CIQ Simulator is not running. Start it first." }
    [void][NativeWin]::ShowWindow($sim.MainWindowHandle, [NativeWin]::SW_RESTORE)
    Wait-Ms 400
    [void][NativeWin]::SetForegroundWindow($sim.MainWindowHandle)
    Wait-Ms 400
    return $sim
}

function Send([string]$keys) {
    [System.Windows.Forms.SendKeys]::SendWait($keys)
}

function Open-ActivityDataPanel {
    Focus-Simulator | Out-Null
    # Menu: Simulation -> Activity Data (accelerators vary by SDK; try common patterns)
    Send("%s")   # Alt+S -> Simulation
    Wait-Ms 250
    Send("a")    # Activity Data
    Wait-Ms 600
}

function Select-GpxSourceAndLoad([string]$path) {
    Focus-Simulator | Out-Null
    # Tab to Data Source combo, open, pick FIT/GPX (usually 2nd item)
    Send("{TAB}{TAB}{TAB}")
    Wait-Ms 200
    Send("{DOWN}{DOWN}{ENTER}")
    Wait-Ms 400
    # Load button — often next tab stop or Space on focused control
    Send("{TAB}{ENTER}")
    Wait-Ms 700
    # File dialog: type full path
    Send($path)
    Wait-Ms 200
    Send("{ENTER}")
    Wait-Ms 800
}

function Start-GpxPlayback {
    Focus-Simulator | Out-Null
    # Play control: bottom-left of Activity Data — try Space after tabs from top
    Send("^{HOME}")  # noop safety
    Wait-Ms 100
    # Shortcut used in many CIQ builds: focus play via repeated Tab from panel start
    for ($i = 0; $i -lt 12; $i++) { Send("{TAB}"); Wait-Ms 40 }
    Send(" ")  # activate play
    Wait-Ms 300
}

function Launch-WatchApp {
    param([string]$AppLabel = "SB_Pastor")
    Focus-Simulator | Out-Null
    # Click center of watch area: simulator window right side (device UI)
    $sim = Get-Process simulator | Select-Object -First 1
    $r = New-Object NativeWin+RECT
    [void][NativeWin]::GetWindowRect($sim.MainWindowHandle, [ref]$r)
    $w = $r.Right - $r.Left
    $h = $r.Bottom - $r.Top
    if ($w -lt 200) { throw "Simulator window looks minimized; restore it manually once." }
    # Watch face ~ right 55% of window, vertical center
    $cx = [int]($r.Left + $w * 0.72)
    $cy = [int]($r.Top + $h * 0.45)
    [System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point($cx, $cy)
    Wait-Ms 150
    # Open app list: long-press simulation = hold click; use keyboard Up from watch home
    [System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point($cx, $cy)
    Wait-Ms 100
    # Menu key on simulated device: use SendKeys to device — Up opens glances, need app menu
    # FR955 in sim: press UP from watch face to open app drawer, then navigate
    Send("{UP}")
    Wait-Ms 400
    Send("{UP}")
    Wait-Ms 400
    Send("{ENTER}")
    Wait-Ms 600
}

Write-Host "[1/5] GPX (Kolya track + Shchuchye buoys)..."
python "$root\scripts\simulate_pastor_route.py"
if (-not (Test-Path $gpx)) { throw "Missing $gpx" }
Write-Host "[2/5] Build SB_Pastor..."
& "$root\connect-iq\setup-sdk-path.bat" | Out-Null
& "$root\scripts\setup-build-link.bat" | Out-Null
Copy-Item -Force "$root\routes\komarovo_shuchye.buoy_route.json" "$root\connect-iq\resources\jsonData\lake_demo.buoy_route.json"
& "X:\bin\monkeyc.bat" -f "$root\connect-iq\monkey.jungle" -o "$root\connect-iq\bin\SB_Pastor.prg" -y "$root\connect-iq\developer_key.der" -d fr955 -w
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
New-Item -ItemType Directory -Force -Path C:\Temp | Out-Null
Copy-Item -Force "$root\connect-iq\bin\SB_Pastor.prg" $prg

Write-Host "[3/5] Simulator..."
$sim = Get-Process -Name simulator -ErrorAction SilentlyContinue
if (-not $sim) {
    Start-Process -FilePath "X:\bin\simulator.exe" -WorkingDirectory "X:\bin"
    Wait-Ms 8000
}

Write-Host "[4/5] Deploy app (monkeydo)..."
& "X:\bin\monkeydo.bat" $prg fr955
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Wait-Ms 2000

Write-Host "[5/5] GUI: Activity Data + GPX + Play..."
try {
    Open-ActivityDataPanel
    Select-GpxSourceAndLoad $gpx
    Start-GpxPlayback
    Launch-WatchApp
    Write-Host ""
    Write-Host "OK. Watch the FR955 window: app should show meters + corridor."
    Write-Host "GPX: $gpx (Kolya, Shchuchye 2026-06-14). See python dry-run for expected vibro times."
} catch {
    Write-Warning "GUI automation failed: $_"
    Write-Host "Manual: Simulation -> Activity Data -> FIT/GPX -> Load $gpx -> Play"
    exit 1
}
