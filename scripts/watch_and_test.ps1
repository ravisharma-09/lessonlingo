$ErrorActionPreference = "Continue"
$PollSeconds = 30
$ReportPath = Join-Path $PSScriptRoot "..\reports\last_run.txt"
$RepositoryRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

Set-Location $RepositoryRoot
New-Item -ItemType Directory -Force (Split-Path $ReportPath) | Out-Null
$LastCommit = git rev-parse HEAD

Write-Host "Watching origin/main every $PollSeconds seconds from commit $LastCommit"

while ($true) {
    Start-Sleep -Seconds $PollSeconds
    git fetch origin main
    $RemoteCommit = git rev-parse origin/main
    if ($RemoteCommit -eq $LastCommit) {
        continue
    }

    & {
        Write-Output "Testing origin/main at $RemoteCommit"
        git reset --hard origin/main
        python -m pip install -q -r requirements.txt
        python -m pytest -q
        python scripts/smoke.py
    } *>&1 | Tee-Object -FilePath $ReportPath

    $LastCommit = $RemoteCommit
    Write-Host "Latest report: $ReportPath"
}
