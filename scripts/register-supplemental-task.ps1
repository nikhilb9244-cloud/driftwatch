<#
.SYNOPSIS
    Register (or remove) a Windows Scheduled Task that collects supplemental element sets.

.DESCRIPTION
    The supplemental covariance can only stop being an extrapolation once the store holds
    versions days apart, and CelesTrak keeps one version and overwrites it. This registers a
    task that runs `driftwatch supplemental` every few hours, which fetches the current
    version (respecting CelesTrak's two-hour floor), stores it under data/supplemental/ and
    thins versions older than a fortnight to one a day.

    The GitHub Actions workflow in .github/workflows/supplemental.yml does the same thing
    once the repository has a remote. This script is the version that runs on a laptop.

.PARAMETER IntervalHours
    How often to run. Default 3, which is inside CelesTrak's floor with room to spare.

.PARAMETER Remove
    Unregister the task instead of creating it.

.EXAMPLE
    pwsh -File scripts/register-supplemental-task.ps1
    pwsh -File scripts/register-supplemental-task.ps1 -IntervalHours 4
    pwsh -File scripts/register-supplemental-task.ps1 -Remove
#>
[CmdletBinding()]
param(
    [int]$IntervalHours = 3,
    [switch]$Remove
)

$ErrorActionPreference = "Stop"
$taskName = "driftwatch-supplemental"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if ($Remove) {
    if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Host "Removed scheduled task '$taskName'."
    }
    else {
        Write-Host "No scheduled task '$taskName' to remove."
    }
    return
}

# Prefer the project's own virtual environment so the task does not depend on uv being on
# the service PATH; fall back to uv if there is no .venv yet.
$venvExe = Join-Path $repo ".venv\Scripts\driftwatch.exe"
if (Test-Path $venvExe) {
    $program = $venvExe
    $arguments = "supplemental"
}
else {
    $uv = (Get-Command uv -ErrorAction SilentlyContinue)
    if (-not $uv) {
        throw "No .venv found at $venvExe and uv is not on PATH. Run 'uv sync' in $repo first."
    }
    $program = $uv.Source
    $arguments = "run driftwatch supplemental"
}

$action = New-ScheduledTaskAction -Execute $program -Argument $arguments -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) `
    -RepetitionInterval (New-TimeSpan -Hours $IntervalHours)
$settings = New-ScheduledTaskSettings -StartWhenAvailable -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings `
    -Description "driftwatch: fetch and store CelesTrak supplemental element sets every $IntervalHours hours." `
    -Force | Out-Null

Write-Host "Registered '$taskName': $program $arguments"
Write-Host "  every $IntervalHours hours, working directory $repo"
Write-Host "  check it with: Get-ScheduledTask -TaskName $taskName | Get-ScheduledTaskInfo"
Write-Host "  run it now with: Start-ScheduledTask -TaskName $taskName"
