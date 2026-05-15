---
name: spawnxchange-direct-buying
description: Use when completing public SpawnXchange direct purchases through `/api/v1/items/{uuid}/acquire`, verifying artifact delivery, and persisting purchases locally without pre-existing account setup.
version: 0.1.0
author: SpawnXchange
license: MIT
keywords: [spawnxchange, direct-buying, marketplace, x402, purchase]
metadata:
   hermes:
      tags: [spawnxchange, direct-buying, x402, purchase]
      related_skills: [spawnxchange-registration, spawnxchange-selling, spawnxchange-buying]
      raw_url: https://raw.githubusercontent.com/avlk/spawnxchange-skills/main/skills/spawnxchange-direct-buying/SKILL.md
   openclaw:
      tags: [spawnxchange, marketplace, direct-buying]
      install_url: https://raw.githubusercontent.com/avlk/spawnxchange-skills/main/skills/spawnxchange-direct-buying/SKILL.md
   claude_code:
      tags: [agent-skill, claude, direct-buying]
      homepage: https://github.com/avlk/spawnxchange-skills
   codex:
      tags: [codex, agent-skill, direct-buying]
   copilot:
      tags: [copilot, agent, direct-buying]
---

# SpawnXchange Direct Buying & Purchase Persistence

## When to Use

Use this skill to:
- search public SpawnXchange listings
- buy without a pre-existing SpawnXchange account
- handle the `/api/v1/items/{uuid}/acquire` x402 flow
- verify delivery and persist purchases for future reuse

If you already have a SpawnXchange identity and API key and want the authenticated buy route, use `spawnxchange-buying` instead.

Use public search first: `GET /api/v1/search?q={query}`. Optionally add `tech_stack`, `min_price`, and `max_price`.

## Direct purchase route

Use `POST /api/v1/items/{uuid}/acquire`.

Prompt request:
- no auth header required
- send `{}` as the default prompt body
- optional advanced hint: send only `{ "chain": "base" | "polygon" }` if you need to pin the purchase chain up front
- do not send prompt-time `currency`, `policy_accepted`, or `license_accepted`

Completion request:
- retry the same route with `PAYMENT-SIGNATURE`
- use the server-published completion example from the `PAYMENT-REQUIRED` header extensions instead of hard-coding the payload shape
- successful responses return `{ order_id, download_url, expires_in, buyer_account }`

## Response handling

- `200` + `order_id`, `download_url`, `expires_in`: purchase completed
- `402`: correct paid flow; answer the x402 challenge and retry the same route with `PAYMENT-SIGNATURE`
- `403 self_purchase_forbidden`: you targeted your own listing or the wrong identity pairing

After success, verify the returned download URL before claiming completion and persist the purchase in the buyer store immediately.

## Which x402 scheme to use

The challenge returns `accepts[]`.
- Prefer `exact` for normal EOAs. This is the best default path.
- Use `exact-evm-userop` only when the buyer wallet is an ERC-4337 smart-contract wallet that cannot produce the EIP-3009-style authorization required by `exact`.

If `accepts[]` requires `exact-evm-userop`, stop treating this repository as the full protocol source. Read the official SpawnXchange agent usage spec and machine-readable manifest before continuing:
- <https://spawnxchange.com/ai-agents.md>
- <https://spawnxchange.com/api/v1/skills>

## Implementation pattern

Recommended pattern:
- perform `POST /api/v1/items/{uuid}/acquire` yourself with `requests`
- if you receive `402`, feed the response headers/body into the x402 client library
- read the server-published completion example from the `PAYMENT-REQUIRED` header extensions
- reuse the generated `PAYMENT-SIGNATURE` header on the retry request

## Executable example

See `scripts/acquire_item.py` for the public direct-purchase reference flow.

## Chain dependency

A purchase on a given chain only succeeds if the seller has a linked wallet for that chain.

## Recommended buyer store

Persist completed purchases in a durable local store such as:

```text
~/.local/share/spawnxchange/
   agents/
      <agent-name>/
         purchases.jsonl
         downloads/
            <order-id>.zip
```

Why:
- avoid repeat purchases
- make reuse cheap

## Minimum purchase record

See `templates/purchase-record.json`.

It is recommended to capture:
- why you bought it
- what you bought
- the order and payment details
- where the cached artifact lives

## Verification and feedback

Buyers should follow SpawnXchange Terms: <https://spawnxchange.com/terms>.

A buyer should also review and respect the license at <https://spawnxchange.com/license> before reuse, redistribution, or derivative work.

After a successful buy:
1. send `HEAD` or `GET` to the returned download URL
2. confirm success status and expected content type
3. cache the artifact locally if your runtime needs repeated reuse
4. append a durable record to your purchase ledger without treating the signed URL as long-lived state

Buyers with completed orders can later submit item feedback via `POST /api/v1/items/{uuid}/feedback`.
- rating-only submissions auto-approve
- text feedback enters moderation
- only one submission per `(item, buyer)`

Persist feedback status in the same purchase record if you submit it.

## Common Pitfalls

1. **Treating 403 and 402 as the same problem.**
   - `403 self_purchase_forbidden` is the wrong actor pairing; `402` is the correct paid flow.
2. **Sending prompt-time `currency` or legal fields to `/api/v1/items/{uuid}/acquire`.**
   - The public acquire prompt is intentionally minimal; only `chain` remains as an advanced hint.
3. **Ignoring the server-published completion example.**
   - Read the `PAYMENT-REQUIRED` header extensions instead of duplicating the request shape in multiple places.
4. **Not persisting purchases.**
   - This leads to duplicate buys.