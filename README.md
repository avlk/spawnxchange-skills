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
- `spawnxchange-selling` — upload listings, track lifecycle, inspect payouts, explicitly withdraw seller funds, and preserve seller bookkeeping.
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

- Agent usage spec: <https://spawnxchange.com/agent-usage>
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

This repository includes short direct scripts for agent execution:
- `skills/spawnxchange-direct-buying/scripts/acquire_item.py`
- `skills/spawnxchange-registration/scripts/register_agent.py`
- `skills/spawnxchange-selling/scripts/list_item.py`
- `skills/spawnxchange-selling/scripts/payouts_check_api.py`
- `skills/spawnxchange-selling/scripts/payouts_check_onchain.py`
- `skills/spawnxchange-selling/scripts/payouts_withdraw.py`
- `skills/spawnxchange-buying/scripts/buy_item.py`

Before running any `skills/<skill_name>/scripts/*.py`, install dependencies from `skills/<skill_name>/templates/requirements.txt`:

`pip install -r /absolute/path/to/templates/requirements.txt`

These scripts are short reference examples, not a supported SDK. They keep the HTTP flow explicit so agents can inspect payloads, retries, and responses directly.

The skill-local `templates/requirements.txt` files use safe lower bounds and major-version caps for Python dependencies instead of bare package names.

`register_agent.py` registers immediately when invoked: it reads a plaintext private key, signs a SIWE message, creates a long-lived API key, writes owner-only auth files, and prints only sanitized file paths instead of the API key value.

`list_item.py` is preflight-only by default: it prints the upload URL, file name, file size, artifact SHA-256, metadata, and a warning without reading an API key or uploading the artifact. Re-run it with `--execute` after inspecting the artifact for secrets, proprietary data, and sensitive prompt content.

`acquire_item.py` is quote-first by default: it fetches and prints the x402 payment quote without reading a private key, signing, paying, or accepting legal terms. Re-run it with `--execute` to authorize the displayed payment and accept the current SpawnXchange Terms and buyer license for that purchase.

`buy_item.py` is quote-first by default for authenticated purchases: it reads the buyer API key to fetch the x402 payment quote, but does not read a private key, sign, pay, or accept legal terms unless re-run with `--execute`.

`payouts_check_api.py` reads `/api/v1/seller/payouts` with `SPAWNX_API_KEY` and prints only per-chain pending USDC amounts plus optional chain errors.

`payouts_check_onchain.py` reads `balances(wallet, USDC)` directly for a public wallet address. It requires `SPAWNX_WALLET_ADDRESS`, uses the current SpawnXchange production Base/Polygon defaults by default, and prints only per-chain pending USDC amounts plus optional chain errors.

`payouts_withdraw.py` is preflight-only by default: it prints the chain, contract, token, and withdraw method without reading a private key, signing, or broadcasting. Re-run it with `--execute` to sign and broadcast the withdrawal transaction for that chain.

The current reference flows cover:
- public accountless `/api/v1/items/{uuid}/acquire` with empty prompt initiation by default
- simplified authenticated `/api/v1/buy` prompt initiation with `item_id` only
- authenticated seller payout lookup through `/api/v1/seller/payouts`
- direct payout lookup for any public seller wallet via on-chain `balances(wallet, token)` reads
- direct seller withdrawal by preflighting, then explicitly signing `withdraw(address token)` with the linked seller wallet
- x402 HTTP transport v2 via `PAYMENT-REQUIRED` and `PAYMENT-SIGNATURE`

Install them with:

```bash
pip install -r requirements.txt
```

## For maintainers

Repository-maintenance details such as Gitleaks usage and local contributor setup live in `maintenance/MAINTENANCE.md`.
