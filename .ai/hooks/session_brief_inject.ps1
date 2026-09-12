# SESSION_BRIEF.md icerigini Claude context'ine inject eder.
# Her session'da sadece bir kez calisir.

$raw = [Console]::In.ReadToEnd()
try {
    $data = $raw | ConvertFrom-Json
    $sessionId = $data.session_id
} catch {
    $sessionId = "unknown"
}

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$projectKey = ($projectRoot.Path -replace '[^a-zA-Z0-9_-]', '_')
$markerPath = Join-Path $env:TEMP "ai_session_${projectKey}_${sessionId}.marker"

if (Test-Path $markerPath) {
    exit 0
}

New-Item -ItemType File -Path $markerPath -Force | Out-Null

$briefPath = Join-Path $projectRoot ".ai\memory\SESSION_BRIEF.md"

if (-not (Test-Path $briefPath)) {
    exit 0
}

$brief = Get-Content $briefPath -Raw -Encoding UTF8

$output = @{
    hookSpecificOutput = @{
        hookEventName = "UserPromptSubmit"
        additionalContext = "=== [AUTO] SESSION_BRIEF.md ===`n$brief`n=== [/SESSION_BRIEF] ==="
    }
}

$output | ConvertTo-Json -Compress -Depth 5

