# Refresh the T-Rank projections and push them.
#
# The build cannot do this itself: barttorvik.com answers GitHub's runners 403
# -- the schedule page and the static ratings file alike, and with a plain
# browser User-Agent -- so it is the address being refused. This machine the
# site will talk to, so it fetches and commits, and the build reads the file.
#
# The push rebuilds the page: lines move during the day, and waiting for the
# 6am build would mean showing this morning's view of tonight's card.
$ErrorActionPreference = "Stop"
$repo   = "C:\Users\kyleh\My Drive\Documents\Claude\sports-daily"
$python = "C:\Users\kyleh\AppData\Local\Programs\Python\Python312-arm64\python.exe"
$log    = Join-Path $repo "refresh-projections.log"
$stamp  = Get-Date -Format "yyyy-MM-dd HH:mm"

function Note($text) { Add-Content -Path $log -Value "$stamp  $text" }

try {
    Set-Location $repo
    # Three weeks is the whole of what the page can show, plus slack. The rest
    # of the season is already in the file and is left where it is.
    $out = & $python "torvik.py" "--refresh" "--days" "21" 2>&1 | Out-String
    $tail = ($out -split "`n" | Where-Object { $_ -match "wrote" } | Select-Object -Last 1).Trim()

    & git add projections.json
    & git diff --cached --quiet projections.json
    if ($LASTEXITCODE -eq 0) {
        Note "no change$(if ($tail) { " ($tail)" })"
        & git reset --quiet
        exit 0
    }
    & git commit --quiet -m "Projections: $(Get-Date -Format 'yyyy-MM-dd')"
    & git pull --quiet --rebase origin main
    & git push --quiet origin main
    Note "pushed. $tail"
} catch {
    Note "FAILED: $($_.Exception.Message)"
    exit 1
}
