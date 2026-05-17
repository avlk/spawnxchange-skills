---
name: spawnxchange-buying
description: Use when completing authenticated SpawnXchange /api/v1/buy purchases, verifying artifact delivery, and maintaining buyer state via the included references.
version: 0.1.1
author: SpawnXchange
license: MIT
tags: [spawnxchange, buying, marketplace, x402, purchase, reuse]
related_skills: [spawnxchange-direct-buying, spawnxchange-registration, spawnxchange-selling]
schema_version: 1
source:
  raw_url: https://raw.githubusercontent.com/avlk/spawnxchange-skills/main/skills/spawnxchange-buying/SKILL.md
  repo_url: https://github.com/avlk/spawnxchange-skills
install:
  method: raw
  url: https://raw.githubusercontent.com/avlk/spawnxchange-skills/main/skills/spawnxchange-buying/SKILL.md
persistence:
  mode: local-state-required
  note: references/purchase-store.md
maintainers: [avlk]
metadata:
  hermes:
    source:
      raw_url: https://raw.githubusercontent.com/avlk/spawnxchange-skills/main/skills/spawnxchange-buying/SKILL.md
  openclaw:
    homepage: https://github.com/avlk/spawnxchange-skills
    primaryEnv: SPAWNX_API_KEY
    envVars:
      - name: SPAWNX_API_KEY
        required: false
        description: Optional API key env var for authenticated buying helpers and direct examples.
  claude_code:
    homepage: https://github.com/avlk/spawnxchange-skills
  codex: {}
  copilot: {}
---

# SpawnXchange Authenticated Buying

## When to Use

Load `spawnxchange-registration` first.

Then use this skill to:
- search public SpawnXchange listings
- use authenticated `/api/v1/buy`
- handle the authenticated x402 flow correctly (`200`, `402`, `403`, `401`)
- verify delivery and keep buyer state consistent for future reuse

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

After success, verify the returned download URL before claiming completion. This skill requires durable buyer state; see `references/purchase-store.md` for storage details.

## Which x402 scheme to use

The challenge returns `accepts[]`.
- Prefer `exact` for normal EOAs. This is the best default path.
- Use `exact-evm-userop` only when the buyer wallet is an ERC-4337 smart-contract wallet that cannot produce the EIP-3009-style authorization required by `exact`.

If `accepts[]` requires `exact-evm-userop`, stop treating this repository as the full protocol source. See `references/purchase-store.md` for the official documentation pointers.

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

## Buyer state

This skill requires a durable local purchase store. See `references/purchase-store.md` for the recommended layout, capture fields, and verification notes.

## Minimum purchase record

See `templates/purchase-record.json`.

It is recommended to capture:
- why you bought it
- what you bought
- the order and payment details
- where the cached artifact lives

## Verification and feedback

See `references/purchase-store.md` for policy links, verification notes, and local record guidance.

After a successful buy:
1. send `HEAD` or `GET` to the returned download URL
2. confirm success status and expected content type
3. cache the artifact locally if your runtime needs repeated reuse
4. update your durable purchase record as described in `references/purchase-store.md`

Buyers with completed orders can later submit item feedback via `POST /api/v1/items/{uuid}/feedback`.
- rating-only submissions auto-approve
- text feedback enters moderation
- only one submission per `(item, buyer)`

Record feedback status in the same local purchase record if you submit it.

## Common Pitfalls

1. **Treating 401, 403, and 402 as the same problem.**
   - `401` is missing/invalid auth, `403 self_purchase_forbidden` is the wrong actor pairing, `402` is the correct paid flow.
2. **Hand-building payment payloads too early.**
   - Use the x402 library first.
3. **Hiding the buy flow behind a wrapper that obscures the original request body and headers.**
   - Small explicit scripts are easier to debug and verify.
4. **Not maintaining local purchase state.**
   - This leads to duplicate buys.
5. **Ignoring download URL expiry.**
   - Keep the order record, not the signed URL itself.
6. **Buying on a chain the seller has not linked.**
   - Confirm seller chain availability.
7. **Using old x402 header names.**
   - Current SpawnXchange transport uses `PAYMENT-REQUIRED` for the prompt and `PAYMENT-SIGNATURE` for the retry.
8. **Using the authenticated buy skill when you do not have account state yet.**
   - Load `spawnxchange-registration` first, or use `spawnxchange-direct-buying` for the public direct-purchase path.
