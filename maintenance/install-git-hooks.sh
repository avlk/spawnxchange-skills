#!/usr/bin/env bash

install_git_hooks() {
  (
    set -euo pipefail

    if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
      echo "Run this from inside a git repository clone." >&2
      exit 1
    fi

    repo_root=$(git rev-parse --show-toplevel)

    hooks_dir="$repo_root/.git/hooks"
    mkdir -p "$hooks_dir"
    install -m 0755 "$repo_root/maintenance/pre-push-gitleaks.sh" "$hooks_dir/pre-push"
    echo "Installed pre-push hook at $hooks_dir/pre-push"
  )
}

install_git_hooks "$@"
