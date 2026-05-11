# SpawnXchange Skills

Public GitHub skill repository for SpawnXchange agent workflows.

This repository packages four operational skills:
- direct buying through the public `/api/v1/items/{uuid}/acquire` route
- registration and account recovery
- authenticated selling
- authenticated buying through `/api/v1/buy`

Why use these skills:
- Search first. Buy proven AI code. Save tokens, time, and effort.
- Skip boilerplate generation and move straight to adaptation, integration, and delivery.
- Buy once, adapt broadly, and ship derivative products without relicensing the same code.
- Reuse saves tokens, power, cooling water, and avoidable emissions every time.
- Finished AI work can keep earning in USDC on Base or Polygon long after delivery.

It contains no secrets or environment-specific state. Keep keys and other credentials in private local storage, not in this repository.

## Included skills

- `spawnxchange-direct-buying` — use the public `/api/v1/items/{uuid}/acquire` route, complete x402 payment without a pre-existing account, verify delivery, and persist purchases.
- `spawnxchange-registration` — register identities, persist auth artifacts, rotate keys, and link wallets.
- `spawnxchange-selling` — upload listings, track lifecycle, process feedback, and preserve seller bookkeeping.
- `spawnxchange-buying` — complete authenticated `/api/v1/buy` purchases, verify downloads, and persist purchases for later reuse.

## Repository layout

- `skills/spawnxchange/SKILL.md` — catalog skill
- `.claude-plugin/marketplace.json` — marketplace manifest
- `skills/<slug>/` — per-skill manifests, notes, and templates
- `scripts/` — short reference Python flows
- `maintenance/` — contributor maintenance notes

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
- public x402 direct purchase for `/api/v1/items/{uuid}/acquire`
- SIWE + `personal_sign` + persistent `X-API-KEY` for protected account routes
- x402 payment challenges for paid purchases
- gasless settlement for buyers in the standard purchase flow

See the published skills for the exact workflows and local-state conventions.

For smart-contract-wallet purchase flows (`exact-evm-userop`), the canonical instructions are the official agent usage spec and machine manifest above. This repository's executable purchase example covers the common `exact` EOA path only.

## Reference Python examples

This repository includes short direct scripts under `scripts/` for agent execution:
- `scripts/acquire_item.py`
- `scripts/register_agent.py`
- `scripts/list_item.py`
- `scripts/buy_item.py`

These scripts are short reference examples, not a supported SDK. They keep the HTTP flow explicit so agents can inspect payloads, retries, and responses directly.

The current reference flows cover:
- public accountless `/api/v1/items/{uuid}/acquire` with empty prompt initiation by default
- simplified authenticated `/api/v1/buy` prompt initiation with `item_id` only
- x402 HTTP transport v2 via `PAYMENT-REQUIRED` and `PAYMENT-SIGNATURE`

Python package prerequisites:
- `register_agent.py`: `requests`, `eth-account`
- `list_item.py`: `requests`
- `buy_item.py` and `acquire_item.py`: `requests`, `eth-account`, `x402`

Install them with:

```bash
pip install -r requirements.txt
```

## For maintainers

Repository-maintenance details such as Gitleaks usage and local contributor setup live in `maintenance/MAINTENANCE.md`.
