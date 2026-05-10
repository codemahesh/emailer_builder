# Ralph loop driver (PowerShell)
#
# Usage:
#   ./docs/issues/issues_1/run.ps1                  # loop until ALL DONE / blocked
#   ./docs/issues/issues_1/run.ps1 -MaxIterations 3 # cap iterations (smoke test)
#   ./docs/issues/issues_1/run.ps1 -DryRun          # print the prompt and exit
#
# Each iteration spawns a FRESH `claude -p` invocation. No context bleed
# between iterations — that is the whole point of Ralph.

param(
  [int]$MaxIterations = 100,
  [switch]$DryRun,
  [string]$Model = 'claude-opus-4-7'
)

$ErrorActionPreference = 'Continue'

$repoRoot   = Resolve-Path (Join-Path $PSScriptRoot '..\..\..')
$promptPath = Join-Path $PSScriptRoot 'PROMPT.md'
$statusPath = Join-Path $PSScriptRoot 'STATUS.md'

if (-not (Test-Path $promptPath)) { throw "Missing $promptPath" }
if (-not (Test-Path $statusPath)) { throw "Missing $statusPath" }

if ($DryRun) {
  Write-Host '--- PROMPT ---'
  Get-Content $promptPath -Raw | Write-Host
  exit 0
}

Set-Location $repoRoot

for ($i = 1; $i -le $MaxIterations; $i++) {
  Write-Host ""
  Write-Host "=== Ralph iteration $i / $MaxIterations ==="
  Write-Host ""

  # Refuse to start a fresh iteration on a dirty tree. The PROMPT also
  # checks this, but a driver-level check fails fast and saves an API call.
  $dirty = git status --porcelain
  if ($dirty) {
    Write-Host "DIRTY TREE — driver halting. Resolve manually:`n$dirty"
    exit 1
  }

  # Stop when STATUS.md says all 10 issues are done.
  if (Select-String -Path $statusPath -Pattern '^\*\*Progress:\*\* 10 / 10' -Quiet) {
    Write-Host "ALL DONE — every issue marked done in STATUS.md."
    exit 0
  }

  # Spawn one fresh Claude iteration. Pipe the prompt via stdin to avoid
  # arg-quoting issues with multi-line prompts on Windows. cmd /c keeps
  # PowerShell's NativeCommandError wrapper out of the way.
  $cmd = "type `"$promptPath`" | claude -p --dangerously-skip-permissions --model $Model"
  cmd /c $cmd

  $exit = $LASTEXITCODE
  if ($exit -ne 0) {
    Write-Host "claude exited with code $exit — driver halting."
    exit $exit
  }

  # If the iteration produced no commit, something is wrong (the prompt
  # mandates at least the claim commit in Step 3). Halt rather than spin.
  $latestCommitTime = git log -1 --format=%ct
  $now = [int][double]::Parse((Get-Date -UFormat %s))
  if (($now - [int]$latestCommitTime) -gt 7200) {
    Write-Host "No new commit in the last 2 hours — likely stuck. Halting."
    exit 1
  }
}

Write-Host "Reached MaxIterations=$MaxIterations without completing all issues."
