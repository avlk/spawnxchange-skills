# SpawnXchange Skills Maintenance

This file is for repository maintainers rather than marketplace users.

## Security automation

This repository uses Gitleaks in two places:
- locally before push via `maintenance/pre-push-gitleaks.sh`
- in GitHub Actions on every `push`, `pull_request`, and manual run via `.github/workflows/security.yml`

### Local setup

Install Gitleaks locally, then install the hook:

```bash
maintenance/install-git-hooks.sh
```

The pre-push hook runs:

```bash
gitleaks detect --no-git --source . --redact --verbose
```

If you prefer to run it manually before pushing:

```bash
gitleaks detect --no-git --source . --redact --verbose
```

## Why maintenance scripts live outside `scripts/`

The top-level `scripts/` directory is reserved for user-facing reference flows that agents may execute directly against SpawnXchange.

Repository-maintenance helpers such as hook installation and secret-scanning setup live under `maintenance/` so they are clearly separated from runtime agent examples.

## Direct links vs mirrored docs

This repository links directly to SpawnXchange upstream docs instead of mirroring local copies.

Why:
- the upstream site is the source of truth
- linking removes copy-maintenance burden
- linking reduces the chance of stale duplicated documentation in the public repo

## Generated wallet skills

The four per-wallet skills — `spawnxchange-circle-wallet`, `spawnxchange-agentcash`,
`spawnxchange-awal` and `spawnxchange-cdp-cli` — are **generated** by
`maintenance/generate-wallet-skills.py`. Do not edit their `SKILL.md` files directly.

Each is a complete, self-contained walkthrough of the SpawnXchange API, because
catalogues install skills individually and an agent that finds one of them should not
need two more to act. The cost of that decision is the same API facts appearing in four
files; the generator is how they are kept from disagreeing.

```bash
python3 maintenance/generate-wallet-skills.py            # check for drift
python3 maintenance/generate-wallet-skills.py --write    # regenerate
```

`maintenance/lint.sh` runs the check, so a hand-edit to a generated file fails CI rather
than being silently overwritten by the next regeneration. When lint reports DRIFT, move
the change into the generator and re-run it with `--write`.

Where a change belongs:

- A fact true of the API for **every** wallet → the shared section templates
  (`HOW_IT_WORKS`, `DISCOVERY`, `BUY`, `SETTLEMENT`, `DELIVERY`, `SELL`, `ACCOUNT`).
- A fact true of **one** CLI → that wallet's entry in `WALLETS` (its `prereq` block, its
  `pitfalls`, its command builder), or `LIST_CMD`.
- A **new** wallet → a command builder, a `WALLETS` entry, a `LIST_CMD` entry, a
  `skills/<slug>/` directory, a `.claude-plugin/marketplace.json` entry in `plugins` and a
  `clawscan-notes.json` note.

To **retire** a skill: replace its body with a redirect, move it out of `plugins` and into
`renames` (mapped to its replacement, or to `null` if there isn't one), and leave the
directory in place. The directory is what ClawHub and Hermes read, and its redirect body is
how installs on those channels learn what replaced it; `renames` is what migrates Claude
Code installs, which never see the body.

Skill `version` values live in the generator and must match `marketplace.json`.
