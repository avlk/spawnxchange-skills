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
- A **new** wallet → a command builder, a `WALLETS` entry with its `bins`, a `LIST_CMD`
  entry, a `skills/<slug>/` directory, a `.claude-plugin/marketplace.json` entry in
  `plugins`, a `clawscan-notes.json` note and a `maintenance/clawhub-taxonomy.json` entry.

To **retire** a skill: replace its body with a redirect, move it out of `plugins` and into
`renames` (mapped to its replacement, or to `null` if there isn't one), and leave the
directory in place. The directory is what ClawHub and Hermes read, and its redirect body is
how installs on those channels learn what replaced it; `renames` is what migrates Claude
Code installs, which never see the body.

Skill `version` values live in the generator and must match `marketplace.json`.

**Do not add `allowed-tools` to frontmatter.** Hermes reads the field's presence as
`high/privilege_escalation` and blocks the install; skills without it scan `safe`. Declare
what a skill runs in `metadata.openclaw.requires.bins` and in its *What this skill runs*
section, and keep that list matching the commands the body actually uses — an incomplete
list is a checkable false claim.

## The pre-publication check reads a folder

`precheck_artifact.py` takes `--folder`, not an archive. Two reasons, both worth keeping:
a fix before packaging costs one command rather than a repackage, and reading a directory
the operator owns means no archive parser and so no zip bombs, traversal or malformed
entries to defend against.

The cost is that it cannot check size — the 10 MB limit is on the packaged archive. The
skills tell the seller to `ls -l` after packaging. Do not have the script build an archive
to find out; it writes nothing, and that is worth more.

`build_listing_body.py` still takes `--archive`, correctly: it builds the upload body from
the packaged file.

## Pinned npm versions

`PINS` in `maintenance/generate-wallet-skills.py` holds the exact version of every wallet
CLI a skill runs. Each setup section installs once at that version; every later example
invokes the installed binary. An unpinned `npx` in a command that signs a USDC payment
lets the code change after review without the version moving, which is the first thing
every scanner flags.

The Circle CLI is the exception: the skill points at Circle's own install instructions and
names the tested version, and `list-artifact.sh` refuses to run without `circle` on PATH
rather than fetching it. Nothing reaches a registry in a signing path.

To bump: read the upstream release notes, change `PINS`, regenerate, bump the affected
skill versions. Never drop a pin to silence a stale-version report.

## ClawHub categories and topics

ClawHub takes both as **publish-time flags**, not frontmatter.
`maintenance/clawhub-taxonomy.json` maps every skill to its `categories` and `topics`, and
the publisher passes them on every release. It lives here because it configures the
publisher: no skill reads it.

Two traps, both of which have bitten this repository:

- **Omitting the flags preserves whatever the registry inferred**, it does not clear it.
  That is how these skills ended up scattered across `other`, `development`, `integrations`
  and `finance`, including two retired tombstones filed under live categories.
- **ClawHub refuses a re-publish at an existing version**, so editing the map alone changes
  nothing already live. A taxonomy fix needs a patch bump to carry it.

Categories come from ClawHub's fixed list, at most three; topics are free-form, at most
five, 48 characters each. `scripts/check_skill_versions.py` in the publisher fails on a
missing skill or an out-of-range value.
