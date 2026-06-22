Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class W {
  public const int SW_RESTORE = 9;
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L,T,R,B; }
}
"@
$p = Get-Process simulator | Select-Object -First 1
[void][W]::ShowWindow($p.MainWindowHandle, 9)
Start-Sleep -Milliseconds 500
$r = New-Object W+RECT
[void][W]::GetWindowRect($p.MainWindowHandle, [ref]$r)
"Rect: L=$($r.L) T=$($r.T) W=$($r.R-$r.L) H=$($r.B-$r.T)"
