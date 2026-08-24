# Registers the "sports daily" scheduled task.
# Run once, from an ELEVATED PowerShell window (Run as administrator):
#   powershell -ExecutionPolicy Bypass -File "C:\Users\kyleh\My Drive\Documents\Claude\sports-daily\register-task.ps1"
#
# Two triggers, same reason as the dynasty task: the machine is not reliably
# on at 07:15, so a logon trigger picks up the days it was off.

$proj = Split-Path -Parent $MyInvocation.MyCommand.Path

$action = New-ScheduledTaskAction -Execute (Join-Path $proj "run-daily.cmd") -WorkingDirectory $proj

$daily = New-ScheduledTaskTrigger -Daily -At 7:15am
$logon = New-ScheduledTaskTrigger -AtLogOn
$logon.Delay = "PT5M"

$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15)

Register-ScheduledTask -TaskName "sports daily" -Action $action `
    -Trigger $daily, $logon -Settings $settings `
    -Description "Builds today's games at sports-daily\output\today.html" -Force

Get-ScheduledTask -TaskName "sports daily" | Select-Object TaskName, State
Write-Host "Registered. Test it with: Start-ScheduledTask -TaskName 'sports daily'"
