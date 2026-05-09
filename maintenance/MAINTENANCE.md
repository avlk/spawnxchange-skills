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