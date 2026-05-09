#!/usr/bin/env bash

run_gitleaks() {
  (
    set -euo pipefail

    if ! command -v gitleaks >/dev/null 2>&1; then
      echo "gitleaks not found in PATH" >&2
      exit 1
    fi

    repo_root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
    cd "$repo_root"

    echo "Running Gitleaks against working tree..."
    gitleaks detect --no-git --source . --redact --verbose

    echo "Gitleaks passed."
  )
}

run_gitleaks "$@"
