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

    # Generate a combined pre-push hook that runs all checks in sequence.
    {
      echo '#!/usr/bin/env bash'
      echo 'set -euo pipefail'
      echo 'repo_root=$(git rev-parse --show-toplevel)'
      echo '"$repo_root/maintenance/pre-push-gitleaks.sh"'
      echo '"$repo_root/maintenance/lint.sh"'
    } > "$hooks_dir/pre-push"
    chmod 0755 "$hooks_dir/pre-push"
    echo "Installed pre-push hook at $hooks_dir/pre-push"
  )
}

install_git_hooks "$@"
