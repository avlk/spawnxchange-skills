#!/usr/bin/env bash

run_lint_checks() {
  (
    set -euo pipefail

    repo_root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
    cd "$repo_root"

    fail=0

    echo "Checking skills/*.md for 'agents.md' references..."
    if grep -rni 'agents\.md' skills/ --include='*.md'; then
      echo "ERROR: Found 'agents.md' reference(s) in skills/ markdown files." >&2
      fail=1
    fi

    echo "Checking Python scripts for os.environ / os.getenv calls..."
    if grep -rn 'os\.environ\|os\.getenv' --include='*.py' skills/; then
      echo "ERROR: Found os.environ/os.getenv call(s) in Python scripts." >&2
      fail=1
    fi

    echo "Checking JS/TS scripts for process.env calls..."
    if grep -rn 'process\.env' --include='*.js' --include='*.ts' skills/; then
      echo "ERROR: Found process.env call(s) in JS/TS scripts." >&2
      fail=1
    fi

    if [ "$fail" -ne 0 ]; then
      exit 1
    fi

    echo "Lint checks passed."
  )
}

run_lint_checks "$@"
