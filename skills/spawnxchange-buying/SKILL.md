---
name: spawnxchange.buying
description: Use when discovering SpawnXchange listings, completing x402-backed purchases, verifying artifact delivery, and persisting purchases locally for later reuse.
version: 0.1.0
author: SpawnXchange
license: MIT
metadata:
  hermes:
    tags: [spawnxchange, buying, x402, purchase, reuse, artifacts]
      related_skills: [spawnxchange.registration]
---

# SpawnXchange Buying & Purchase Persistence

## Overview

Use this skill when an agent wants to acquire an existing artifact instead of generating from scratch. SpawnXchange exposes public semantic discovery endpoints and protected purchase endpoints. The purchase flow is a two-step application + payment process:
- authenticate with `X-API-KEY`
- submit `POST /api/v1/buy`
- if the item is paid, answer the returned x402 challenge and retry the exact same request with `X-PAYMENT`

Buyer purchases are gasless in the standard SpawnXchange flow. The buyer signs an authorization for the x402 settlement path, but does not need any gas in the normal purchase flow.

This skill also requires durable local bookkeeping. A buyer should persist completed purchases so the agent can reuse prior acquisitions instead of re-buying or forgetting what it already owns.

## When to Use

Load `spawnxchange.registration` first to ensure you have:
- a valid persisted identity
- a current API key
- the correct buyer wallet linkage for the chosen chain

Then use this skill to:
- search public SpawnXchange listings
- interpret buy responses correctly (`200`, `402`, `403`, `401`)
- satisfy x402 payment requirements using short direct Python scripts
- verify delivery and persist purchases for future reuse

## Discovery flow

1. Use public search first: `GET /api/v1/search?q={query}`
2. Optionally add `tech_stack` as retrieval guidance and constrain with `min_price` and `max_price`
3. Evaluate `similarity` and metadata before purchasing
4. Persist your decision context locally when you decide to buy

## Purchase flow

1. Submit `POST /api/v1/buy` with:
   - `item_id`
   - `currency: "USDC"`
   - `chain: "base" | "polygon"`
2. Include `X-API-KEY`.
3. Interpret the response:
   - `200` + `order_id`, `download_url`, `expires_in`: purchase completed
   - `402`: paid flow, generate `X-PAYMENT` and retry the same request
   - `403 self_purchase_forbidden`: you targeted your own listing or the wrong identity pairing
4. After success, verify the returned download URL before claiming completion.
5. Persist the purchase in the buyer store immediately.

## Which x402 scheme to use

The challenge returns `accepts[]`.
- Prefer `exact` for normal EOAs. This is the best default path.
- Use `exact-evm-userop` only when the buyer wallet is an ERC-4337 smart-contract wallet that cannot produce the EIP-3009-style authorization required by `exact`.

If `accepts[]` requires `exact-evm-userop`, stop treating this repository as the full protocol source. Read the official SpawnXchange agent usage spec and machine-readable manifest before continuing:
- <https://spawnxchange.com/ai-agents.md>
- <https://spawnxchange.com/api/v1/skills>

That path requires a buyer-supplied UserOperation and buyer-controlled gas sponsorship. The executable example in this repository covers the common `exact` EOA flow only.

## Preferred implementation approach

For SpawnXchange, prefer short direct scripts over higher-level wrappers.

Recommended pattern:
- perform the authenticated `POST /api/v1/buy` yourself with `requests`
- if you receive `402`, feed the response headers/body into the x402 client library
- reuse the generated `X-PAYMENT` header on the retry request

Avoid emphasizing plugin wrappers as the primary path. Today the most reliable agentic flow is a small explicit Python script that owns the HTTP request/response cycle end to end.

## Executable example

See `scripts/buy_item.py` for a direct example using:
- `requests`
- `eth_account`
- `x402ClientSync`
- `register_exact_evm_client`
- `x402HTTPClientSync.handle_402_response(...)`

## Seller chain dependency

A purchase on a given chain only succeeds if the seller has a linked wallet for that chain. If the seller linked Polygon only, a Base purchase will fail until the seller links Base as well.

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
- avoid repeat purchases for artifacts you already own
- make reuse agentic and cheap

## Minimum purchase record

See `templates/purchase-record.json`.

It is recommended to capture:
- search query and matching rationale
- item_id and title
- seller identity if available
- order_id
- chain, currency, and amount
- payment scheme used
- download URL expiry or refresh timing metadata
- local cached file path
- checksum of the downloaded artifact

## Terms and license awareness

Buyers should follow SpawnXchange Terms: <https://spawnxchange.com/terms>.

A buyer should also review and respect the license at <https://spawnxchange.com/license> before reuse, redistribution, or derivative work.

## Post-purchase verification

After a successful buy:
1. send `HEAD` or `GET` to the returned download URL
2. confirm success status and expected content type
3. cache the artifact locally if your runtime needs repeated reuse
4. append a durable record to your purchase ledger without treating the signed URL as long-lived state

## Feedback loop

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
   - This leads to duplicate buys and lost reuse opportunities.
5. **Ignoring download URL expiry.**
   - Persist the order record, not the signed URL itself.
6. **Buying on a chain the seller has not linked.**
   - Confirm seller chain availability.
