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

    echo "Checking buy_snippet.py pins and malformed-input handling..."
    if ! python3 -B - <<'PYEOF'
import importlib.util, sys
sys.path.insert(0, "skills/spawnxchange-selling/scripts")
import buy_snippet as b
spec = importlib.util.spec_from_file_location("gen", "maintenance/generate-wallet-skills.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)
bad = []
for const, key in (("SKILLS_PIN", "skills"), ("AGENTCASH_PIN", "agentcash"), ("AWAL_PIN", "awal")):
    if getattr(b, const) != gen.PINS[key]:
        bad.append(f"{const}={getattr(b, const)} but PINS[{key!r}]={gen.PINS[key]}")
good = {"status": "active", "metadata": {"title": "t", "prices": {"USDC": 1.25}},
        "available_chains": ["base", "polygon"]}
cases = {
    "NaN": {**good, "metadata": {"prices": {"USDC": "NaN"}}},
    "Infinity": {**good, "metadata": {"prices": {"USDC": "Infinity"}}},
    "list price": {**good, "metadata": {"prices": {"USDC": [1]}}},
    "zero": {**good, "metadata": {"prices": {"USDC": 0}}},
    "bool": {**good, "metadata": {"prices": {"USDC": True}}},
    "metadata not dict": {**good, "metadata": "x"},
    "prices not dict": {**good, "metadata": {"prices": 3}},
    "chains not list": {**good, "available_chains": "base"},
    "chains unhashable": {**good, "available_chains": [["base"]]},
    "no known chain": {**good, "available_chains": ["solana"]},
}
for name, payload in cases.items():
    try:
        b.summarize("0ad6e69a-af04-428e-83fc-6a6125e26da7", payload)
        bad.append(f"{name}: accepted")
    except b.SnippetError:
        pass
    except Exception as err:
        bad.append(f"{name}: {type(err).__name__}")
for url in ("https://[::1", "javascript:alert(1)", "http://example.com/x"):
    try:
        b.parse_chooser_url(url)
        bad.append(f"chooser url {url}: accepted")
    except b.SnippetError:
        pass
    except Exception as err:
        bad.append(f"chooser url {url}: {type(err).__name__}")
try:
    b.parse_item_id("0ad6e69a-af04-428e-83fc-6a6125e26da7\n")
    bad.append("item id with trailing newline accepted")
except b.SnippetError:
    pass
summary = b.summarize("0ad6e69a-af04-428e-83fc-6a6125e26da7", good)
if b.atomic(summary["price"]) != "1250000":
    bad.append("atomic(1.25)")
polygon = b.summarize("0ad6e69a-af04-428e-83fc-6a6125e26da7", {**good, "available_chains": ["polygon"]})
if any(w[0] == "awal" for w in b.ways_for(polygon)):
    bad.append("awal offered for a polygon-only item")
for line in bad:
    print("  " + line, file=sys.stderr)
sys.exit(1 if bad else 0)
PYEOF
    then
      echo "ERROR: buy_snippet.py pins or input handling failed the self-check." >&2
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
