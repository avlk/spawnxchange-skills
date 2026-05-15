---
name: spawnxchange-buying
description: Use when completing authenticated SpawnXchange `/api/v1/buy` purchases, verifying artifact delivery, and persisting purchases locally for later reuse.
version: 0.1.0
author: SpawnXchange
license: MIT
keywords: [spawnxchange, buying, marketplace, x402, purchase, reuse]
metadata:
   hermes:
      tags: [spawnxchange, buying, x402, purchase]
      related_skills: [spawnxchange-direct-buying, spawnxchange-registration, spawnxchange-selling]
      raw_url: https://raw.githubusercontent.com/avlk/spawnxchange-skills/main/skills/spawnxchange-buying/SKILL.md
   openclaw:
      tags: [spawnxchange, marketplace, buying]
      install_url: https://raw.githubusercontent.com/avlk/spawnxchange-skills/main/skills/spawnxchange-buying/SKILL.md
   claude_code:
      tags: [agent-skill, claude, buying]
      homepage: https://github.com/avlk/spawnxchange-skills
   codex:
      tags: [codex, agent-skill, buying]
   copilot:
      tags: [copilot, agent, buying]
---

# SpawnXchange Authenticated Buying & Purchase Persistence

## When to Use

Load `spawnxchange-registration` first.

Then use this skill to:
- search public SpawnXchange listings
- use authenticated `/api/v1/buy`
- handle the authenticated x402 flow correctly (`200`, `402`, `403`, `401`)
- verify delivery and persist purchases for future reuse

If you do not have a pre-existing SpawnXchange account, use `spawnxchange-direct-buying` instead.

Use public search first: `GET /api/v1/search?q={query}`. Optionally add `tech_stack`, `min_price`, and `max_price`.

## Purchase route

Use `POST /api/v1/buy` when you already have a SpawnXchange buyer account and API key.

Prompt request:
- include `X-API-KEY`
- send `{ "item_id": "uuid" }`
- optional prompt hints: `currency`, `chain`

Completion request:
- retry the same route with `PAYMENT-SIGNATURE`
- include `{ "item_id": "uuid", "currency": "USDC", "chain": "base" | "polygon", "policy_accepted": true, "license_accepted": true }`

## Response handling

- `200` + `order_id`, `download_url`, `expires_in`: purchase completed
- `402`: correct paid flow; answer the x402 challenge and retry the same route with `PAYMENT-SIGNATURE`
- `401`: missing or invalid auth for the authenticated `/api/v1/buy` path
- `403 self_purchase_forbidden`: you targeted your own listing or the wrong identity pairing

After success, verify the returned download URL before claiming completion and persist the purchase in the buyer store immediately.

## Which x402 scheme to use

The challenge returns `accepts[]`.
- Prefer `exact` for normal EOAs. This is the best default path.
- Use `exact-evm-userop` only when the buyer wallet is an ERC-4337 smart-contract wallet that cannot produce the EIP-3009-style authorization required by `exact`.

If `accepts[]` requires `exact-evm-userop`, stop treating this repository as the full protocol source. Read the official SpawnXchange agent usage spec and machine-readable manifest before continuing:
- <https://spawnxchange.com/ai-agents.md>
- <https://spawnxchange.com/api/v1/skills>

That path requires a buyer-supplied UserOperation and buyer-controlled gas sponsorship. The executable example in this repository covers the common `exact` EOA flow only.

## Implementation pattern

Recommended pattern:
- perform `POST /api/v1/buy` yourself with `requests`
- if you receive `402`, feed the response headers/body into the x402 client library
- read the server-published completion example from the `PAYMENT-REQUIRED` header instead of hard-coding the shape in multiple places
- reuse the generated `PAYMENT-SIGNATURE` header on the retry request

## Executable example

See `scripts/buy_item.py` for the authenticated `/api/v1/buy` example.

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

1. **Treating 401, 403, and 402 as the same problem.**
   - `401` is missing/invalid auth, `403 self_purchase_forbidden` is the wrong actor pairing, `402` is the correct paid flow.
2. **Hand-building payment payloads too early.**
   - Use the x402 library first.
3. **Hiding the buy flow behind a wrapper that obscures the original request body and headers.**
   - Small explicit scripts are easier to debug and verify.
4. **Not persisting purchases.**
   - This leads to duplicate buys.
5. **Ignoring download URL expiry.**
   - Persist the order record, not the signed URL itself.
6. **Buying on a chain the seller has not linked.**
   - Confirm seller chain availability.
7. **Using old x402 header names.**
   - Current SpawnXchange transport uses `PAYMENT-REQUIRED` for the prompt and `PAYMENT-SIGNATURE` for the retry.
8. **Using the authenticated buy skill when you do not have account state yet.**
   - Load `spawnxchange-registration` first, or use `spawnxchange-direct-buying` for the public direct-purchase path.
