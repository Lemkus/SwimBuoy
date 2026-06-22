Add-Type @"
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public class EnumWin {
  public delegate bool Callback(IntPtr hWnd, IntPtr lParam);
  [DllImport("user32.dll")] public static extern bool EnumWindows(Callback cb, IntPtr lParam);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr hWnd, StringBuilder sb, int max);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT r);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
}
"@
$pid = (Get-Process simulator | Select-Object -First 1).Id
$list = New-Object System.Collections.Generic.List[string]
$cb = [EnumWin+Callback]{
  param($h,$l)
  $out = 0u
  [EnumWin]::GetWindowThreadProcessId($h, [ref]$out) | Out-Null
  if ($out -eq $pid -and [EnumWin]::IsWindowVisible($h)) {
    $sb = New-Object System.Text.StringBuilder 256
    [EnumWin]::GetWindowText($h, $sb, 256) | Out-Null
    $r = New-Object EnumWin+RECT
    [EnumWin]::GetWindowRect($h, [ref]$r) | Out-Null
    $list.Add(("'{0}' {1}x{2} @ {3},{4}" -f $sb.ToString(), ($r.Right-$r.Left), ($r.Bottom-$r.Top), $r.Left, $r.Top))
  }
  return $true
}
[EnumWin]::EnumWindows($cb, [IntPtr]::Zero) | Out-Null
$list
