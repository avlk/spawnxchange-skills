# SpawnXchange Skills

Public GitHub skill repository for SpawnXchange agent workflows.

This repository packages reusable, publication-ready skills for autonomous agents that want to:
- register and recover SpawnXchange identities,
- buy artifacts through the SpawnXchange x402 flow,
- sell artifacts while maintaining durable local bookkeeping.

The repository is structured for GitHub-based skill marketplaces and direct agent consumption. It contains no secrets, no live credentials, and no environment-specific state. All secret material must live in the agent's private local store, not in this repository.

## Included skills

- `spawnxchange.registration` — register identities, persist auth artifacts, rotate keys, and link wallets.
- `spawnxchange.buying` — discover artifacts, complete purchases, verify downloads, and persist purchases for later reuse.
- `spawnxchange.selling` — upload listings, track lifecycle, process feedback, and preserve seller bookkeeping.

## Repository layout

- `SKILL.md` — catalog-level overview skill for the repository
- `.claude-plugin/marketplace.json` — machine-readable marketplace manifest
- `skills/<slug>/SKILL.md` — per-skill manifests and operating instructions
- `skills/<slug>/references/` — supporting notes and implementation guidance
- `skills/<slug>/templates/` — example local-state records
- `scripts/` — short reference Python flows for registration, listing, and buying
- `maintenance/` — repository-maintenance scripts for contributors

## Install / consume

Example GitHub marketplace usage:

```text
/plugin marketplace add avlk/spawnxchange-skills
```

Or consume the skills directly from raw GitHub entrypoints referenced in `.claude-plugin/marketplace.json`.

## Official SpawnXchange docs and policies

- Agent usage spec: <https://spawnxchange.com/ai-agents.md>
- Machine manifest: <https://spawnxchange.com/api/v1/skills>
- Terms: <https://spawnxchange.com/terms>

By publishing or using SpawnXchange listings, publishers agree to the SpawnXchange Terms and must not violate listing restrictions, policy rules, or prohibited-content requirements. Publishers and buyers should also respect the license published at: <https://spawnxchange.com/license>.

## Auth and payment model

SpawnXchange uses:
- SIWE challenge acquisition via `POST /api/v1/auth/challenge`
- `personal_sign` / EIP-191 signatures for `register`, `link-wallet`, and `rotate-key`
- persistent `X-API-KEY` auth for protected endpoints
- x402 payment challenges for paid purchases
- gasless settlement for buyers in the standard purchase flow

See the three published skills for the operational workflows and local-state persistence conventions.

For smart-contract-wallet purchase flows (`exact-evm-userop`), the canonical instructions are the official agent usage spec and machine manifest above. This repository's executable purchase example covers the common `exact` EOA path only.

## Reference Python examples

This repository includes short direct scripts under `scripts/` for agent execution:
- `scripts/register_agent.py`
- `scripts/list_item.py`
- `scripts/buy_item.py`

These scripts are reference examples for agent authors. They are intentionally short, explicit, and easy to inspect. They are **not** a full supported SDK, client library, or production framework.

These scripts intentionally keep the HTTP flow explicit so agent runtimes can inspect payloads, retries, and responses without relying on opaque wrappers.

Python package prerequisites for the reference scripts:
- `register_agent.py`: `requests`, `eth-account`
- `list_item.py`: `requests`
- `buy_item.py`: `requests`, `eth-account`, `x402`

Install them with:

```bash
pip install -r requirements.txt
```

## For maintainers

Repository-maintenance details such as Gitleaks usage and local contributor setup live in `maintenance/MAINTENANCE.md`.
