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

    echo "Checking md and shell scripts for unsafe curl calls..."
    if grep -rniE 'curl\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)' --include='*.sh' --include='*.md' skills/; then
      echo "ERROR: Found potentially unsafe curl call(s) in shell scripts or markdown files." >&2
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

    echo "Checking the precheck never prints a matched secret..."
    probe=$(mktemp -d)
    printf 'AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMIKcanaryEXAMPLEKEY\nDB_PASSWORD=hunter2canary\n' \
      > "$probe/.env"
    if python3 skills/spawnxchange-selling/scripts/precheck_artifact.py --folder "$probe" \
         2>&1 | grep -qE 'wJalrXUtnFEMIKcanary|hunter2canary'; then
      echo "ERROR: precheck_artifact.py printed a matched secret. It must report the" >&2
      echo "       file and line only — this output reaches transcripts and CI logs." >&2
      fail=1
    fi
    rm -rf "$probe"

    echo "Checking the precheck stops when its scan budget runs out..."
    probe=$(mktemp -d)
    for i in $(seq -w 1 520); do truncate -s 131072 "$probe/f$i.txt"; done
    printf 'API_KEY = "abcdefghijklmnopqrstuvwxyz"\n' > "$probe/zz.py"
    out=$(python3 skills/spawnxchange-selling/scripts/precheck_artifact.py --folder "$probe" 2>&1 || true)
    if ! printf '%s\n' "$out" | grep -q 'were not examined'; then
      echo "ERROR: precheck_artifact.py passed files it never examined:" >&2
      printf '%s\n' "$out" | head -20 >&2
      fail=1
    fi
    rm -rf "$probe"

    echo "Checking the precheck reports author and copyright lines..."
    probe=$(mktemp -d)
    printf '"""Ledger.\n\nCopyright (c) 2026 SomeHandle.\n"""\n' > "$probe/a.py"
    printf '__author__ = "x"\n' > "$probe/b.py"
    printf '/**\n * @author someone\n */\n' > "$probe/c.js"
    printf '# Tool\n\n\xc2\xa9 Someone\n' > "$probe/README.md"
    out=$(python3 skills/spawnxchange-selling/scripts/precheck_artifact.py --folder "$probe" 2>&1 || true)
    if ! printf '%s\n' "$out" | grep -q 'an author or copyright line (4)'; then
      echo "ERROR: precheck_artifact.py missed an author or copyright line:" >&2
      printf '%s\n' "$out" >&2
      fail=1
    fi
    rm -rf "$probe"
    probe=$(mktemp -d)
    printf 'def f(c):\n    return g(c) + 2026\n\nrows.sort(key=lambda r: r.date)  # sorted by date\nauthors = []\n' \
      > "$probe/a.py"
    if python3 skills/spawnxchange-selling/scripts/precheck_artifact.py --folder "$probe" \
         2>&1 | grep -q 'author or copyright'; then
      echo "ERROR: precheck_artifact.py reported an author line in ordinary code." >&2
      fail=1
    fi
    rm -rf "$probe"

    echo "Checking each skill's permissions match what its scripts do..."
    if ! python3 maintenance/check-tool-scope.py skills; then
      fail=1
    fi

    # SkillSpector's "Skill Enumeration" rule (AS3) reads any skills/<name>/SKILL.md
    # path as one skill reading another's instructions, our own URLs included.
    echo "Checking skills for skills/<name>/SKILL.md paths..."
    if grep -rniE 'skills?/[A-Z][A-Za-z0-9_-]+/SKILL\.md' skills/; then
      echo "ERROR: a skills/<name>/SKILL.md path is flagged as Skill Enumeration by ClawHub's scanner; link the repository instead."
      fail=1
    fi

    echo "Checking generated wallet skills are in sync with their template..."
    if ! python3 maintenance/generate-wallet-skills.py; then
      echo "ERROR: wallet SKILL.md files differ from maintenance/generate-wallet-skills.py." >&2
      fail=1
    fi

    if [ "$fail" -ne 0 ]; then
      exit 1
    fi

    echo "Lint checks passed."
  )
}

run_lint_checks "$@"
