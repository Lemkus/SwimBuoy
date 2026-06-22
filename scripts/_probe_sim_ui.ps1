Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

function Walk($el, $depth) {
    if ($depth -gt 7) { return }
    $name = $el.Current.Name
    $ctype = $el.Current.ControlType.ProgrammaticName
    if ($name -or $ctype -match 'Button|Menu|Combo|Edit|Tab|List') {
        $pad = ' ' * ($depth * 2)
        Write-Output ("{0}{1} | '{2}'" -f $pad, $ctype, $name)
    }
    $children = $el.FindAll([System.Windows.Automation.TreeScope]::Children, [System.Windows.Automation.Condition]::TrueCondition)
    foreach ($c in $children) { Walk $c ($depth + 1) }
}

$root = [System.Windows.Automation.AutomationElement]::RootElement
$cond = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::NameProperty, 'CIQ Simulator')
$sim = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $cond)
if (-not $sim) {
    Write-Output 'Simulator window not found'
    exit 1
}
Walk $sim 0
