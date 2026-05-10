#!/usr/bin/env bash
# Ralph loop driver (bash)
#
# Usage:
#   ./docs/issues/issues_1/run.sh                # loop until ALL DONE / blocked
#   MAX_ITERATIONS=3 ./docs/issues/issues_1/run.sh
#   DRY_RUN=1 ./docs/issues/issues_1/run.sh      # print the prompt and exit

set -euo pipefail

MAX_ITERATIONS="${MAX_ITERATIONS:-100}"
MODEL="${MODEL:-claude-opus-4-7}"
DRY_RUN="${DRY_RUN:-0}"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../../.." && pwd)"
prompt_path="$script_dir/PROMPT.md"
status_path="$script_dir/STATUS.md"

[[ -f "$prompt_path" ]] || { echo "Missing $prompt_path"; exit 1; }
[[ -f "$status_path" ]] || { echo "Missing $status_path"; exit 1; }

prompt="$(cat "$prompt_path")"

if [[ "$DRY_RUN" == "1" ]]; then
  echo '--- PROMPT ---'
  echo "$prompt"
  exit 0
fi

cd "$repo_root"

for ((i = 1; i <= MAX_ITERATIONS; i++)); do
  echo
  echo "=== Ralph iteration $i / $MAX_ITERATIONS ==="
  echo

  if [[ -n "$(git status --porcelain)" ]]; then
    echo "DIRTY TREE — driver halting. Resolve manually:"
    git status --porcelain
    exit 1
  fi

  if grep -q '^\*\*Progress:\*\* 10 / 10' "$status_path"; then
    echo "ALL DONE — every issue marked done in STATUS.md."
    exit 0
  fi

  claude -p "$prompt" \
    --dangerously-skip-permissions \
    --model "$MODEL"

  latest_commit_ts="$(git log -1 --format=%ct)"
  now_ts="$(date +%s)"
  if (( now_ts - latest_commit_ts > 7200 )); then
    echo "No new commit in the last 2 hours — likely stuck. Halting."
    exit 1
  fi
done

echo "Reached MAX_ITERATIONS=$MAX_ITERATIONS without completing all issues."
